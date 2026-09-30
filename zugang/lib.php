<?php
/**
 * Zugangsschutz für /edit/ (Bearbeitungszugang): Allowlist + Einmalcode per E-Mail.
 */

declare(strict_types=1);

require_once dirname(__DIR__) . '/redaktion/lib.php';

define('HVW_ACCESS_FILE', HVW_ROOT . '/redaktion/storage/access-emails.json');
define('HVW_OTP_FILE', HVW_ROOT . '/redaktion/storage/otp.json');
define('HVW_ZUGANG_SECRET_FILE', HVW_ROOT . '/redaktion/storage/zugang-secret.txt');
define('HVW_MAIL_CONFIG', HVW_ROOT . '/redaktion/config.mail.php');
define('HVW_ZUGANG_TZ', 'Europe/Zurich');

/**
 * Ordner-URLs auf index.php oder index.html auflösen.
 * /redaktion/ hat nur index.php — nicht index.html.
 */
function hvw_zugang_resolve_index(string $rel): string
{
    $rel = '/' . ltrim($rel, '/');
    $dirPath = HVW_ROOT . rtrim($rel, '/');
    $isDir = $rel === '/' || str_ends_with($rel, '/') || is_dir($dirPath);
    if (!$isDir) {
        return $rel;
    }
    $dir = rtrim($rel, '/');
    foreach (['index.php', 'index.html'] as $index) {
        $candidate = ($dir === '' ? '' : $dir) . '/' . $index;
        if (is_file(HVW_ROOT . $candidate)) {
            return $candidate;
        }
    }
    return ($dir === '' ? '' : $dir) . '/index.html';
}

function hvw_zugang_timezone(): DateTimeZone
{
    return new DateTimeZone(HVW_ZUGANG_TZ);
}

/** Unix-Zeitpunkt der nächsten Mitternacht (Europe/Zurich). */
function hvw_zugang_day_end(?int $now = null): int
{
    $tz = hvw_zugang_timezone();
    $nowDt = (new DateTimeImmutable('@' . ($now ?? time())))->setTimezone($tz);
    return $nowDt->modify('tomorrow')->setTime(0, 0, 0)->getTimestamp();
}

function hvw_zugang_base(): string
{
    $script = str_replace('\\', '/', (string) ($_SERVER['SCRIPT_NAME'] ?? '/zugang/serve.php'));
    $base = preg_replace('#/zugang/serve\.php$#', '', $script);
    return is_string($base) ? rtrim($base, '/') : '';
}

function hvw_zugang_rel(): string
{
    $uri = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH) ?: '/';
    $base = hvw_zugang_base();
    if ($base !== '' && str_starts_with($uri, $base)) {
        $uri = substr($uri, strlen($base)) ?: '/';
    }
    $uri = '/' . ltrim($uri, '/');
    return hvw_zugang_resolve_index($uri);
}

function hvw_default_access_emails(): array
{
    return [
        'thomas.giger@hvwinterthur.ch',
        'christian.huggenberg@hvwinterthur.ch',
        'gioia.joehri@hvwinterthur.ch',
    ];
}

function hvw_mail_config(): array
{
    $defaults = [
        'host' => '',
        'port' => 587,
        'user' => '',
        'pass' => '',
        'secure' => 'tls',
        'from' => 'noreply@hvwinterthur.ch',
        'from_name' => 'HVW Vorschau',
        'allowed_emails' => hvw_default_access_emails(),
    ];
    if (!is_file(HVW_MAIL_CONFIG)) {
        return $defaults;
    }
    $cfg = require HVW_MAIL_CONFIG;
    if (!is_array($cfg)) {
        return $defaults;
    }
    $merged = array_merge($defaults, $cfg);
    if (empty($merged['allowed_emails']) || !is_array($merged['allowed_emails'])) {
        $merged['allowed_emails'] = hvw_default_access_emails();
    }
    return $merged;
}

function hvw_normalize_email(string $email): string
{
    return strtolower(trim($email));
}

function hvw_access_emails(): array
{
    $data = hvw_read_json(HVW_ACCESS_FILE);
    $emails = $data['emails'] ?? null;
    if (!is_array($emails)) {
        $seed = array_merge(hvw_default_access_emails(), (array) (hvw_mail_config()['allowed_emails'] ?? []));
        $emails = [];
        foreach ($seed as $item) {
            $n = hvw_normalize_email((string) $item);
            if ($n !== '' && filter_var($n, FILTER_VALIDATE_EMAIL)) {
                $emails[] = $n;
            }
        }
        $emails = array_values(array_unique($emails));
        if ($emails) {
            hvw_write_access_emails($emails);
        }
        return $emails;
    }
    $out = [];
    foreach ($emails as $item) {
        $n = hvw_normalize_email((string) $item);
        if ($n !== '' && filter_var($n, FILTER_VALIDATE_EMAIL)) {
            $out[] = $n;
        }
    }
    return array_values(array_unique($out));
}

function hvw_write_access_emails(array $emails): void
{
    $clean = [];
    foreach ($emails as $item) {
        $n = hvw_normalize_email((string) $item);
        if ($n !== '' && filter_var($n, FILTER_VALIDATE_EMAIL)) {
            $clean[] = $n;
        }
    }
    $clean = array_values(array_unique($clean));
    hvw_write_json(HVW_ACCESS_FILE, [
        'updatedAt' => gmdate('Y-m-d\TH:i:s\Z'),
        'emails' => $clean,
    ]);
}

function hvw_email_allowed(string $email): bool
{
    $n = hvw_normalize_email($email);
    return $n !== '' && in_array($n, hvw_access_emails(), true);
}

function hvw_zugang_secret(): string
{
    if (is_file(HVW_ZUGANG_SECRET_FILE)) {
        $secret = trim((string) file_get_contents(HVW_ZUGANG_SECRET_FILE));
        if ($secret !== '') {
            return $secret;
        }
    }
    $secret = bin2hex(random_bytes(32));
    $dir = dirname(HVW_ZUGANG_SECRET_FILE);
    if (!is_dir($dir)) {
        mkdir($dir, 0775, true);
    }
    file_put_contents(HVW_ZUGANG_SECRET_FILE, $secret, LOCK_EX);
    return $secret;
}

function hvw_zugang_cookie_name(): string
{
    return 'hvw_zugang';
}

/** Session nur am Kalendertag gültig, dessen Mitternacht in $exp steht. */
function hvw_zugang_session_valid(int $exp, ?int $now = null): bool
{
    $now = $now ?? time();
    return $exp > $now && $exp === hvw_zugang_day_end($now);
}

function hvw_zugang_set_cookie(string $email): void
{
    $exp = hvw_zugang_day_end();
    $payload = $exp . '|' . hvw_normalize_email($email);
    $sig = hash_hmac('sha256', $payload, hvw_zugang_secret());
    $value = rtrim(strtr(base64_encode($payload . '|' . $sig), '+/', '-_'), '=');
    $secure = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off');
    setcookie(hvw_zugang_cookie_name(), $value, [
        'expires' => $exp,
        'path' => hvw_cookie_path(),
        'secure' => $secure,
        'httponly' => true,
        'samesite' => 'Lax',
    ]);
}

function hvw_zugang_clear_cookie(): void
{
    $secure = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off');
    setcookie(hvw_zugang_cookie_name(), '', [
        'expires' => time() - 3600,
        'path' => hvw_cookie_path(),
        'secure' => $secure,
        'httponly' => true,
        'samesite' => 'Lax',
    ]);
}

function hvw_zugang_ok(): bool
{
    $raw = $_COOKIE[hvw_zugang_cookie_name()] ?? '';
    if ($raw === '') {
        return false;
    }
    $pad = strlen($raw) % 4;
    if ($pad) {
        $raw .= str_repeat('=', 4 - $pad);
    }
    $decoded = base64_decode(strtr($raw, '-_', '+/'), true);
    if (!is_string($decoded) || !str_contains($decoded, '|')) {
        return false;
    }
    $parts = explode('|', $decoded);
    if (count($parts) !== 3) {
        return false;
    }
    [$exp, $email, $sig] = $parts;
    if (!ctype_digit($exp) || !hvw_zugang_session_valid((int) $exp)) {
        return false;
    }
    $payload = $exp . '|' . $email;
    $expect = hash_hmac('sha256', $payload, hvw_zugang_secret());
    return hash_equals($expect, $sig) && hvw_email_allowed($email);
}

function hvw_otp_issue(string $email): string
{
    $email = hvw_normalize_email($email);
    $code = str_pad((string) random_int(0, 999999), 6, '0', STR_PAD_LEFT);
    $data = hvw_read_json(HVW_OTP_FILE);
    $now = time();
    $last = (int) (($data[$email]['sentAt'] ?? 0));
    if ($last && ($now - $last) < 60) {
        throw new RuntimeException('Bitte eine Minute warten, bevor Sie einen neuen Code anfordern.');
    }
    $hourCount = (int) (($data[$email]['hourCount'] ?? 0));
    $hourStart = (int) (($data[$email]['hourStart'] ?? 0));
    if ($hourStart < $now - 3600) {
        $hourCount = 0;
        $hourStart = $now;
    }
    if ($hourCount >= 5) {
        throw new RuntimeException('Zu viele Codes. Bitte später erneut versuchen.');
    }
    $data[$email] = [
        'hash' => password_hash($code, PASSWORD_DEFAULT),
        'exp' => hvw_zugang_day_end($now),
        'tries' => 0,
        'sentAt' => $now,
        'hourCount' => $hourCount + 1,
        'hourStart' => $hourStart,
    ];
    hvw_write_json(HVW_OTP_FILE, $data);
    return $code;
}

function hvw_otp_verify(string $email, string $code): bool
{
    $email = hvw_normalize_email($email);
    $code = preg_replace('/\s+/', '', $code) ?? '';
    $data = hvw_read_json(HVW_OTP_FILE);
    $row = $data[$email] ?? null;
    if (!is_array($row)) {
        return false;
    }
    if ((int) ($row['exp'] ?? 0) < time()) {
        unset($data[$email]);
        hvw_write_json(HVW_OTP_FILE, $data);
        return false;
    }
    $tries = (int) ($row['tries'] ?? 0);
    if ($tries >= 5) {
        unset($data[$email]);
        hvw_write_json(HVW_OTP_FILE, $data);
        return false;
    }
    $ok = password_verify($code, (string) ($row['hash'] ?? ''));
    if ($ok) {
        unset($data[$email]);
        hvw_write_json(HVW_OTP_FILE, $data);
        return true;
    }
    $data[$email]['tries'] = $tries + 1;
    hvw_write_json(HVW_OTP_FILE, $data);
    return false;
}

function hvw_send_access_code(string $email, string $code): void
{
    $cfg = hvw_mail_config();
    $subject = 'Ihr Zugangscode für die HVW-Vorschau';
    $body = "Guten Tag\n\nIhr Code für die interne Vorschau des Historischen Vereins Winterthur lautet:\n\n  {$code}\n\nEr gilt bis Mitternacht (Schweizer Zeit) und kann nur einmal verwendet werden. Am nächsten Tag brauchen Sie einen neuen Code.\n\nWenn Sie diesen Code nicht angefordert haben, können Sie die Nachricht ignorieren.\n\nHistorischer Verein Winterthur\n";
    $from = (string) $cfg['from'];
    $fromName = (string) $cfg['from_name'];
    if ((string) $cfg['host'] !== '' && (string) $cfg['user'] !== '' && (string) $cfg['pass'] !== '') {
        hvw_smtp_send($cfg, $email, $subject, $body);
        return;
    }
    $headers = [
        'MIME-Version: 1.0',
        'Content-Type: text/plain; charset=UTF-8',
        'From: ' . sprintf('"%s" <%s>', addcslashes($fromName, '"\\'), $from),
    ];
    $ok = @mail($email, '=?UTF-8?B?' . base64_encode($subject) . '?=', $body, implode("\r\n", $headers));
    if (!$ok) {
        throw new RuntimeException('E-Mail konnte nicht gesendet werden. SMTP-Zugangsdaten in den GitHub-Secrets prüfen.');
    }
}

function hvw_smtp_expect($fp, array $ok): string
{
    $data = '';
    while (!feof($fp)) {
        $line = fgets($fp, 1024);
        if ($line === false) {
            break;
        }
        $data .= $line;
        if (preg_match('/^\d{3} /', $line)) {
            break;
        }
    }
    $code = (int) substr($data, 0, 3);
    if (!in_array($code, $ok, true)) {
        throw new RuntimeException('Mailserver: unerwartete Antwort (' . trim($data) . ').');
    }
    return $data;
}

function hvw_smtp_cmd($fp, string $cmd, array $ok): string
{
    fwrite($fp, $cmd . "\r\n");
    return hvw_smtp_expect($fp, $ok);
}

function hvw_smtp_send(array $cfg, string $to, string $subject, string $body): void
{
    $host = (string) $cfg['host'];
    $port = (int) $cfg['port'];
    $user = (string) $cfg['user'];
    $pass = (string) $cfg['pass'];
    $from = (string) $cfg['from'];
    $fromName = (string) $cfg['from_name'];
    $secure = (string) $cfg['secure'];
    $remote = ($secure === 'ssl') ? "ssl://{$host}:{$port}" : "tcp://{$host}:{$port}";
    $fp = @stream_socket_client($remote, $errno, $errstr, 20, STREAM_CLIENT_CONNECT);
    if (!$fp) {
        throw new RuntimeException("SMTP-Verbindung fehlgeschlagen ({$errstr}).");
    }
    stream_set_timeout($fp, 20);
    hvw_smtp_expect($fp, [220]);
    $ehlo = 'EHLO hvwinterthur.ch';
    hvw_smtp_cmd($fp, $ehlo, [250]);
    if ($secure === 'tls') {
        hvw_smtp_cmd($fp, 'STARTTLS', [220]);
        if (!stream_socket_enable_crypto($fp, true, STREAM_CRYPTO_METHOD_TLS_CLIENT)) {
            throw new RuntimeException('SMTP STARTTLS fehlgeschlagen.');
        }
        hvw_smtp_cmd($fp, $ehlo, [250]);
    }
    hvw_smtp_cmd($fp, 'AUTH LOGIN', [334]);
    hvw_smtp_cmd($fp, base64_encode($user), [334]);
    hvw_smtp_cmd($fp, base64_encode($pass), [235]);
    hvw_smtp_cmd($fp, 'MAIL FROM:<' . $from . '>', [250]);
    hvw_smtp_cmd($fp, 'RCPT TO:<' . $to . '>', [250, 251]);
    hvw_smtp_cmd($fp, 'DATA', [354]);
    $encodedSubject = '=?UTF-8?B?' . base64_encode($subject) . '?=';
    $msg = 'From: "' . addcslashes($fromName, '"\\') . '" <' . $from . ">\r\n";
    $msg .= 'To: <' . $to . ">\r\n";
    $msg .= 'Subject: ' . $encodedSubject . "\r\n";
    $msg .= "MIME-Version: 1.0\r\n";
    $msg .= "Content-Type: text/plain; charset=UTF-8\r\n";
    $msg .= "\r\n" . str_replace("\n.", "\n..", str_replace("\r\n", "\n", $body)) . "\r\n.";
    fwrite($fp, $msg . "\r\n");
    hvw_smtp_expect($fp, [250]);
    hvw_smtp_cmd($fp, 'QUIT', [221, 250]);
    fclose($fp);
}
