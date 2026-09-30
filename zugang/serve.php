<?php
declare(strict_types=1);

require_once __DIR__ . '/lib.php';

function hvw_zugang_denied(): never
{
    http_response_code(403);
    header('Content-Type: text/plain; charset=UTF-8');
    echo 'Zugriff verweigert.';
    exit;
}

function hvw_zugang_layout(string $title, string $inner): void
{
    $esc = static fn (string $s): string => htmlspecialchars($s, ENT_QUOTES, 'UTF-8');
    header('Content-Type: text/html; charset=UTF-8');
    header('Cache-Control: no-store');
    echo '<!DOCTYPE html><html lang="de-CH"><head><meta charset="UTF-8">';
    echo '<meta name="viewport" content="width=device-width, initial-scale=1">';
    echo '<meta name="robots" content="noindex,nofollow">';
    echo '<title>' . $esc($title) . '</title>';
    $base = hvw_zugang_base();
    $prefix = ($base === '' ? '' : $base) . '/';
    echo '<link rel="icon" href="' . $esc($prefix) . 'images/favicon.ico">';
    echo '<link rel="stylesheet" href="' . $esc($prefix) . 'css/fonts.css">';
    echo '<script src="https://cdn.tailwindcss.com"></script>';
    echo '<script src="' . $esc($prefix) . 'js/tailwind-config.js"></script>';
    echo '<link rel="stylesheet" href="' . $esc($prefix) . 'css/site.css">';
    echo '</head><body class="bg-hvw-fog font-sans text-hvw-ink antialiased">';
    echo '<main class="mx-auto flex min-h-screen max-w-md flex-col justify-center px-5 py-12">';
    echo $inner;
    echo '</main></body></html>';
}

function hvw_zugang_form(string $error, string $step, string $email): void
{
    $esc = static fn (string $s): string => htmlspecialchars($s, ENT_QUOTES, 'UTF-8');
    $inner = '<p class="text-sm font-semibold uppercase tracking-[0.08em] text-hvw-mute">Historischer Verein Winterthur</p>';
    $inner .= '<h1 class="mt-2 text-3xl font-semibold">Interne Vorschau</h1>';
    $inner .= '<p class="mt-3 text-hvw-mute">Nur hinterlegte E-Mail-Adressen erhalten einen Code. Der Zugang gilt bis Mitternacht; am nächsten Tag ist ein neuer Code nötig. Für das Bearbeiten von Texten bleiben die Logins Redaktion und Freigabe.</p>';
    if ($error !== '') {
        $inner .= '<p class="mt-6 border border-red-700 bg-red-50 px-4 py-3 text-red-800" role="alert">' . $esc($error) . '</p>';
    }
    $inner .= '<form method="post" class="mt-8 border border-hvw-ink bg-white p-6">';
    if ($step === 'code') {
        $inner .= '<input type="hidden" name="hvw_step" value="code">';
        $inner .= '<input type="hidden" name="email" value="' . $esc($email) . '">';
        $inner .= '<p class="text-sm text-hvw-mute">Code an <strong>' . $esc($email) . '</strong> gesendet (falls berechtigt). Er gilt bis Mitternacht.</p>';
        $inner .= '<label class="mt-4 block text-sm font-semibold" for="code">Code aus der E-Mail</label>';
        $inner .= '<input class="mt-2 min-h-12 w-full border border-hvw-ink px-4 text-base tracking-[0.3em]" id="code" name="code" inputmode="numeric" autocomplete="one-time-code" required maxlength="8">';
        $inner .= '<button class="mt-6 min-h-12 w-full bg-hvw-ink font-semibold text-white hover:bg-hvw-charcoal" type="submit">Eintreten</button>';
        $inner .= '<p class="mt-4 text-sm"><button class="underline" type="submit" name="hvw_step" value="email" formnovalidate>Andere Adresse</button></p>';
    } else {
        $inner .= '<input type="hidden" name="hvw_step" value="email">';
        $inner .= '<label class="block text-sm font-semibold" for="email">E-Mail-Adresse</label>';
        $inner .= '<input class="mt-2 min-h-12 w-full border border-hvw-ink px-4 text-base" id="email" name="email" type="email" required autocomplete="email" value="' . $esc($email) . '">';
        $inner .= '<button class="mt-6 min-h-12 w-full bg-hvw-ink font-semibold text-white hover:bg-hvw-charcoal" type="submit">Code senden</button>';
    }
    $inner .= '</form>';
    hvw_zugang_layout('Vorschau — Historischer Verein Winterthur', $inner);
}

function hvw_zugang_dispatch(): void
{
    $rel = hvw_zugang_rel();
    if (str_starts_with($rel, '/zugang/')) {
        $base = hvw_zugang_base();
        header('Location: ' . ($base === '' ? '/' : $base . '/'), true, 302);
        exit;
    }
    if (str_contains($rel, '..') || str_contains($rel, "\0")) {
        hvw_zugang_denied();
    }
    $blocked = [
        '/redaktion/storage/',
        '/redaktion/config.local.php',
        '/redaktion/config.mail.php',
        '/redaktion/lib.php',
        '/zugang/lib.php',
        '/.htaccess',
        '/.htpasswd',
    ];
    foreach ($blocked as $b) {
        if (str_starts_with($rel, $b) || $rel === $b) {
            hvw_zugang_denied();
        }
    }
    $full = HVW_ROOT . $rel;
    $root = realpath(HVW_ROOT);
    if (is_file($full)) {
        $real = realpath($full);
        if ($real === false || $root === false || !str_starts_with($real, $root)) {
            hvw_zugang_denied();
        }
        $full = $real;
    } elseif (!is_file($full)) {
        http_response_code(404);
        header('Content-Type: text/plain; charset=UTF-8');
        echo 'Nicht gefunden.';
        exit;
    }

    if (str_ends_with(strtolower($full), '.php')) {
        $base = hvw_zugang_base();
        $_SERVER['SCRIPT_FILENAME'] = $full;
        $_SERVER['SCRIPT_NAME'] = $base . $rel;
        $_SERVER['PHP_SELF'] = $base . $rel;
        chdir(dirname($full));
        require $full;
        return;
    }

    $mime = 'application/octet-stream';
    if (function_exists('mime_content_type')) {
        $detected = mime_content_type($full);
        if (is_string($detected) && $detected !== '') {
            $mime = $detected;
        }
    }
    $map = [
        'html' => 'text/html; charset=UTF-8',
        'json' => 'application/json; charset=UTF-8',
        'css' => 'text/css; charset=UTF-8',
        'js' => 'application/javascript; charset=UTF-8',
        'svg' => 'image/svg+xml',
        'pdf' => 'application/pdf',
        'txt' => 'text/plain; charset=UTF-8',
        'xml' => 'application/xml',
        'ico' => 'image/x-icon',
        'png' => 'image/png',
        'jpg' => 'image/jpeg',
        'jpeg' => 'image/jpeg',
        'webp' => 'image/webp',
        'gif' => 'image/gif',
        'woff2' => 'font/woff2',
    ];
    $ext = strtolower(pathinfo($full, PATHINFO_EXTENSION));
    if (isset($map[$ext])) {
        $mime = $map[$ext];
    }
    header('Content-Type: ' . $mime);
    header('X-Content-Type-Options: nosniff');
    if (in_array($ext, ['html', 'json', 'js', 'css'], true)) {
        header('Cache-Control: no-store, max-age=0');
    }
    readfile($full);
}

if (($_GET['logout'] ?? '') === '1' || ($_POST['hvw_step'] ?? '') === 'logout') {
    hvw_zugang_clear_cookie();
    $base = hvw_zugang_base();
    header('Location: ' . ($base === '' ? '/' : $base . '/'), true, 302);
    exit;
}

if (hvw_zugang_ok()) {
    hvw_zugang_dispatch();
    exit;
}

$error = '';
$step = 'email';
$email = hvw_normalize_email((string) ($_POST['email'] ?? $_GET['email'] ?? ''));

if (($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
    $posted = (string) ($_POST['hvw_step'] ?? 'email');
    if ($posted === 'email') {
        usleep(200000);
        if (hvw_email_allowed($email)) {
            try {
                $code = hvw_otp_issue($email);
                hvw_send_access_code($email, $code);
            } catch (Throwable $e) {
                $error = $e->getMessage();
            }
        }
        if ($error === '') {
            $step = 'code';
        }
    } elseif ($posted === 'code') {
        usleep(200000);
        $code = (string) ($_POST['code'] ?? '');
        if (hvw_email_allowed($email) && hvw_otp_verify($email, $code)) {
            hvw_zugang_set_cookie($email);
            $uri = $_SERVER['REQUEST_URI'] ?? '/';
            $uri = preg_replace('/[?&]email=[^&]*/', '', $uri) ?? $uri;
            header('Location: ' . $uri, true, 302);
            exit;
        }
        $error = 'Code ungültig oder abgelaufen.';
        $step = 'code';
    }
}

hvw_zugang_form($error, $step, $email);
