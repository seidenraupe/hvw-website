<?php
/**
 * HVW-Redaktion: Auth, Speichern, Freigabe.
 */

declare(strict_types=1);

define('HVW_ROOT', dirname(__DIR__));
define('HVW_SCHEMA', HVW_ROOT . '/data/content-schema.json');
define('HVW_LIVE', HVW_ROOT . '/data/content-live.json');
define('HVW_DRAFT', __DIR__ . '/storage/content-draft.json');
define('HVW_UPLOADS', HVW_ROOT . '/data/uploads');
define('HVW_ALLOWED_TAGS', ['strong', 'em', 'u', 'br', 'a']);
define('HVW_IMAGE_PLACEHOLDER', 'images/placeholder-event-1.svg');

function hvw_cookie_path(): string
{
    $script = str_replace('\\', '/', (string) ($_SERVER['SCRIPT_NAME'] ?? '/'));
    $base = preg_replace('#/zugang/serve\.php$#', '', $script);
    $base = preg_replace('#/redaktion(?:/.*)?$#', '', is_string($base) ? $base : $script);
    if (!is_string($base) || $base === '') {
        return '/';
    }
    return rtrim($base, '/') . '/';
}

function hvw_boot_session(): void
{
    if (session_status() === PHP_SESSION_ACTIVE) {
        return;
    }
    $secure = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off');
    session_name('hvw_redaktion');
    session_set_cookie_params([
        'lifetime' => 0,
        'path' => hvw_cookie_path(),
        'secure' => $secure,
        'httponly' => true,
        'samesite' => 'Lax',
    ]);
    session_start();
    if (empty($_SESSION['csrf'])) {
        $_SESSION['csrf'] = bin2hex(random_bytes(16));
    }
}

function hvw_users(): array
{
    $users = [
        'redaktion' => [
            'role' => 'redaktion',
            'name' => 'Redaktion',
            'hash' => '$2y$10$JsbUkaA9zXuQnZLCk2IFbuuEf7FQD3yqf4yvqhFGz.3AXHEqqg/fW',
        ],
        'freigabe' => [
            'role' => 'freigabe',
            'name' => 'Freigabe',
            'hash' => '$2y$10$7BnB6ia5KzRATNupk9pUx.vV3B/LWCqqIknLFyScwBMVNWC5jR7Ge',
        ],
    ];
    $local = __DIR__ . '/config.local.php';
    if (is_file($local)) {
        $override = require $local;
        if (is_array($override) && $override) {
            $users = $override;
        }
    }
    return $users;
}

function hvw_user(): ?array
{
    hvw_boot_session();
    if (empty($_SESSION['user'])) {
        return null;
    }
    $id = (string) $_SESSION['user'];
    $users = hvw_users();
    if (!isset($users[$id])) {
        return null;
    }
    return [
        'id' => $id,
        'role' => $users[$id]['role'],
        'name' => $users[$id]['name'],
        'csrf' => $_SESSION['csrf'],
    ];
}

function hvw_require_user(): array
{
    $user = hvw_user();
    if (!$user) {
        hvw_json(['ok' => false, 'error' => 'Bitte anmelden.'], 401);
    }
    return $user;
}

function hvw_require_csrf(): void
{
    $sent = $_SERVER['HTTP_X_CSRF_TOKEN'] ?? '';
    if (!hash_equals((string) ($_SESSION['csrf'] ?? ''), (string) $sent)) {
        hvw_json(['ok' => false, 'error' => 'Sitzung abgelaufen. Bitte neu anmelden.'], 403);
    }
}

function hvw_json(array $payload, int $status = 200): void
{
    http_response_code($status);
    header('Content-Type: application/json; charset=UTF-8');
    header('Cache-Control: no-store');
    echo json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

function hvw_read_json(string $path): array
{
    if (!is_file($path)) {
        return [];
    }
    $raw = file_get_contents($path);
    $data = json_decode((string) $raw, true);
    return is_array($data) ? $data : [];
}

function hvw_write_json(string $path, array $data): void
{
    $dir = dirname($path);
    if (!is_dir($dir) && !mkdir($dir, 0775, true) && !is_dir($dir)) {
        throw new RuntimeException('Speicherordner fehlt.');
    }
    $json = json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PRETTY_PRINT);
    if ($json === false) {
        throw new RuntimeException('JSON konnte nicht geschrieben werden.');
    }
    $tmp = $path . '.tmp';
    if (file_put_contents($tmp, $json . "\n", LOCK_EX) === false) {
        throw new RuntimeException('Datei konnte nicht gespeichert werden.');
    }
    if (!rename($tmp, $path)) {
        throw new RuntimeException('Datei konnte nicht ersetzt werden.');
    }
}

function hvw_rueckblick_max(): int
{
    return 48;
}

function hvw_rueckblick_field_defs(int $n): array
{
    $optional = $n > 6;
    $label = 'Agenda · Rückblick ' . $n;
    return [
        "agenda.rueckblick.{$n}.image" => [
            'label' => $label . ' · Bild',
            'page' => 'agenda.html',
            'max' => 180,
            'rich' => false,
            'multiline' => false,
            'type' => 'image',
            'optional' => true,
        ],
        "agenda.rueckblick.{$n}.kicker" => [
            'label' => $label . ' · Kategorie',
            'page' => 'agenda.html',
            'max' => 60,
            'rich' => false,
            'multiline' => false,
            'optional' => $optional,
        ],
        "agenda.rueckblick.{$n}.title" => [
            'label' => $label . ' · Titel',
            'page' => 'agenda.html',
            'max' => 80,
            'rich' => false,
            'multiline' => false,
            'optional' => $optional,
        ],
        "agenda.rueckblick.{$n}.body" => [
            'label' => $label . ' · Text',
            'page' => 'agenda.html',
            'max' => 600,
            'rich' => true,
            'multiline' => true,
            'optional' => $optional,
        ],
        "agenda.rueckblick.{$n}.location" => [
            'label' => $label . ' · Ort',
            'page' => 'agenda.html',
            'max' => 60,
            'rich' => false,
            'multiline' => false,
            'optional' => $optional,
        ],
    ];
}

function hvw_extend_schema_from_fields(array $schema, array $fields): array
{
    $max = hvw_rueckblick_max();
    $slots = [];
    foreach (array_keys($fields) as $id) {
        if (preg_match('/^agenda\.rueckblick\.(\d+)\./', (string) $id, $m)) {
            $n = (int) $m[1];
            if ($n >= 1 && $n <= $max) {
                $slots[$n] = true;
            }
        }
    }
    foreach ($slots as $n => $_keep) {
        foreach (hvw_rueckblick_field_defs($n) as $id => $meta) {
            if (!isset($schema[$id])) {
                $schema[$id] = $meta;
            }
        }
    }
    return $schema;
}

function hvw_schema(): array
{
    $data = hvw_read_json(HVW_SCHEMA);
    $fields = $data['fields'] ?? [];
    $fields = is_array($fields) ? $fields : [];
    $extra = [];
    if (is_file(HVW_LIVE)) {
        $extra = array_merge($extra, hvw_live()['fields'] ?? []);
    }
    if (is_file(HVW_DRAFT)) {
        $extra = array_merge($extra, hvw_draft()['fields'] ?? []);
    }
    return hvw_extend_schema_from_fields($fields, $extra);
}

function hvw_plain_len(string $html): int
{
    $text = html_entity_decode(strip_tags($html), ENT_QUOTES | ENT_HTML5, 'UTF-8');
    $text = preg_replace('/\s+/u', ' ', trim($text)) ?? '';
    return function_exists('mb_strlen') ? mb_strlen($text) : strlen($text);
}

function hvw_safe_rich_href(string $href): string
{
    $href = preg_replace('/[\x00-\x1F\x7F]/', '', $href) ?? '';
    $href = preg_replace('/\s+/', '', $href) ?? '';
    if ($href === '' || strlen($href) > 500) {
        return '';
    }
    if (preg_match('#^(javascript|data|vbscript):#i', $href) || str_contains($href, '\\') || str_starts_with($href, '//')) {
        return '';
    }
    if (str_starts_with($href, '#')) {
        return preg_match('/^#[A-Za-z0-9_-]+$/', $href) ? $href : '';
    }
    if (preg_match('#^[a-z][a-z0-9+.-]*:#i', $href)) {
        $parts = parse_url($href);
        if (!is_array($parts)) {
            return '';
        }
        $scheme = strtolower((string) ($parts['scheme'] ?? ''));
        if (!in_array($scheme, ['http', 'https'], true) || isset($parts['user']) || isset($parts['pass'])) {
            return '';
        }
        $host = (string) ($parts['host'] ?? '');
        if ($host === '' || !str_contains($host, '.')) {
            return '';
        }
        return $href;
    }
    if (str_contains($href, '..') || str_contains($href, ':')) {
        return '';
    }
    if (!preg_match('@^(?:\./|/)?[A-Za-z0-9][A-Za-z0-9._~/-]*(?:\?[A-Za-z0-9._~%=&+-]*)?(?:#[A-Za-z0-9_-]+)?$@', $href)) {
        return '';
    }
    return $href;
}

function hvw_rename_element(DOMElement $el, string $tag): DOMElement
{
    $next = $el->ownerDocument->createElement($tag);
    while ($el->firstChild) {
        $next->appendChild($el->firstChild);
    }
    $el->parentNode?->replaceChild($next, $el);
    return $next;
}

function hvw_unwrap_element(DOMElement $el): void
{
    $parent = $el->parentNode;
    if (!$parent) {
        return;
    }
    while ($el->firstChild) {
        $parent->insertBefore($el->firstChild, $el);
    }
    $parent->removeChild($el);
}

function hvw_strip_attributes(DOMElement $el): void
{
    while ($el->attributes->length > 0) {
        $el->removeAttribute($el->attributes->item(0)->nodeName);
    }
}

function hvw_sanitize_rich_children(DOMNode $parent): void
{
    $child = $parent->firstChild;
    while ($child) {
        $next = $child->nextSibling;
        if ($child->nodeType !== XML_ELEMENT_NODE) {
            if ($child->nodeType !== XML_TEXT_NODE) {
                $parent->removeChild($child);
            }
            $child = $next;
            continue;
        }
        /** @var DOMElement $el */
        $el = $child;
        $tag = strtolower($el->nodeName);
        if (in_array($tag, ['script', 'style', 'iframe', 'object', 'embed'], true)) {
            $parent->removeChild($el);
            $child = $next;
            continue;
        }
        if ($tag === 'b' || $tag === 'i') {
            $el = hvw_rename_element($el, $tag === 'b' ? 'strong' : 'em');
            $tag = strtolower($el->nodeName);
        }
        if ($tag === 'span' || $tag === 'font') {
            $style = strtolower($el->getAttribute('style'));
            $wraps = [];
            if (preg_match('/text-decoration(?:-line)?\s*:[^;]*underline/', $style)) {
                $wraps[] = 'u';
            }
            if (preg_match('/font-style\s*:\s*italic/', $style)) {
                $wraps[] = 'em';
            }
            if (preg_match('/font-weight\s*:\s*(bold|bolder|[6-9]00)/', $style)) {
                $wraps[] = 'strong';
            }
            if ($wraps) {
                $doc = $el->ownerDocument;
                $inner = $doc->createElement($wraps[0]);
                while ($el->firstChild) {
                    $inner->appendChild($el->firstChild);
                }
                $current = $inner;
                for ($i = 1, $n = count($wraps); $i < $n; $i++) {
                    $outer = $doc->createElement($wraps[$i]);
                    $outer->appendChild($current);
                    $current = $outer;
                }
                $el->appendChild($current);
            }
            $marker = $el->ownerDocument->createTextNode('');
            $el->parentNode?->insertBefore($marker, $el);
            hvw_unwrap_element($el);
            $child = $marker->nextSibling;
            $marker->parentNode?->removeChild($marker);
            continue;
        }
        if (!in_array($tag, HVW_ALLOWED_TAGS, true)) {
            hvw_sanitize_rich_children($el);
            $marker = $el->ownerDocument->createTextNode('');
            $el->parentNode?->insertBefore($marker, $el);
            hvw_unwrap_element($el);
            $child = $marker->nextSibling;
            $marker->parentNode?->removeChild($marker);
            continue;
        }
        if ($tag === 'a') {
            $href = hvw_safe_rich_href($el->getAttribute('href'));
            $nested = false;
            for ($p = $el->parentNode; $p instanceof DOMElement; $p = $p->parentNode) {
                if (strtolower($p->nodeName) === 'a') {
                    $nested = true;
                    break;
                }
            }
            hvw_strip_attributes($el);
            if ($href === '' || $nested) {
                hvw_sanitize_rich_children($el);
                $marker = $el->ownerDocument->createTextNode('');
                $el->parentNode?->insertBefore($marker, $el);
                hvw_unwrap_element($el);
                $child = $marker->nextSibling;
                $marker->parentNode?->removeChild($marker);
                continue;
            }
            $el->setAttribute('href', $href);
            if (preg_match('#^https?://#i', $href) || preg_match('@\.pdf(?:$|[?#])@i', $href)) {
                $el->setAttribute('target', '_blank');
                $el->setAttribute('rel', 'noopener noreferrer');
            }
            hvw_sanitize_rich_children($el);
            $child = $el->nextSibling;
            continue;
        }
        hvw_strip_attributes($el);
        if ($tag !== 'br') {
            hvw_sanitize_rich_children($el);
        }
        $child = $el->nextSibling;
    }
}

function hvw_sanitize_rich(string $html): string
{
    $html = preg_replace('/[\x00-\x08\x0B\x0C\x0E-\x1F]/', '', $html) ?? '';
    if (trim($html) === '') {
        return '';
    }
    $doc = new DOMDocument();
    $prev = libxml_use_internal_errors(true);
    $doc->loadHTML(
        '<?xml encoding="UTF-8"><html><body><div id="hvw-rich-root">' . $html . '</div></body></html>',
        LIBXML_HTML_NODEFDTD
    );
    libxml_clear_errors();
    libxml_use_internal_errors($prev);
    $root = $doc->getElementById('hvw-rich-root');
    if (!$root) {
        return '';
    }
    hvw_sanitize_rich_children($root);
    $out = '';
    foreach ($root->childNodes as $child) {
        $out .= $doc->saveHTML($child);
    }
    $out = preg_replace_callback('/&#(\d+);/', static function (array $m): string {
        $cp = (int) $m[1];
        return $cp >= 128 ? mb_chr($cp, 'UTF-8') : $m[0];
    }, $out) ?? $out;
    $out = preg_replace_callback('/&#x([0-9a-f]+);/i', static function (array $m): string {
        $cp = hexdec($m[1]);
        return $cp >= 128 ? mb_chr($cp, 'UTF-8') : $m[0];
    }, $out) ?? $out;
    $out = preg_replace('/^(?:\s|<br\s*\/?>)+/i', '', $out) ?? $out;
    $out = preg_replace('/(?:\s|<br\s*\/?>)+$/i', '', $out) ?? $out;
    return trim($out);
}

function hvw_sanitize_plain(string $html): string
{
    $text = html_entity_decode(strip_tags($html), ENT_QUOTES | ENT_HTML5, 'UTF-8');
    $text = preg_replace('/\s+/u', ' ', trim($text)) ?? '';
    return $text;
}

function hvw_is_image_field(array $meta): bool
{
    return ($meta['type'] ?? '') === 'image';
}

function hvw_is_url_field(array $meta): bool
{
    return ($meta['type'] ?? '') === 'url';
}

function hvw_sanitize_url(string $value): string
{
    $value = hvw_sanitize_plain($value);
    if ($value === '' || !preg_match('#^https://#i', $value)) {
        return '';
    }
    $parts = parse_url($value);
    if (!is_array($parts) || empty($parts['host']) || isset($parts['user']) || isset($parts['pass'])) {
        return '';
    }
    $host = (string) $parts['host'];
    if (!preg_match('/^[\p{L}0-9.-]+$/u', $host) || !str_contains($host, '.')) {
        return '';
    }
    $path = (string) ($parts['path'] ?? '');
    if (str_contains($path, '..')) {
        return '';
    }
    $query = isset($parts['query']) ? '?' . $parts['query'] : '';
    return 'https://' . $host . $path . $query;
}

function hvw_is_optional_field(array $meta): bool
{
    return !empty($meta['optional']) || hvw_is_image_field($meta);
}

function hvw_sanitize_image_path(string $value): string
{
    $value = hvw_sanitize_plain($value);
    if ($value === '') {
        return '';
    }
    $value = str_replace('\\', '/', $value);
    if (str_contains($value, '..') || str_starts_with($value, '/') || str_contains($value, ':')) {
        return '';
    }
    if (preg_match('#^images/placeholder-event-[1-6]\.svg$#', $value)) {
        return $value;
    }
    if (preg_match('#^images/placeholder-sammlung-[1-3]\.svg$#', $value)) {
        return $value;
    }
    if (preg_match('#^images/sammlung-(ausstellung|titelbild|house)\.jpg$#', $value)) {
        return $value;
    }
    if (preg_match('#^images/placeholder-museum-(lindengut|moersburg|schaffen)\.svg$#', $value)) {
        return $value;
    }
    if (preg_match('#^images/museen/(museum-lindengut|schloss-moersburg|museum-schaffen)\.jpg$#', $value)) {
        return $value;
    }
    if (preg_match('#^images/placeholder-partner\.svg$#', $value)) {
        return $value;
    }
    if (preg_match('#^images/partner/(logo|bild)-(?:[1-9]|1[0-4])\.jpg$#', $value)) {
        return $value;
    }
    if (preg_match('#^images/partner/hero-(?:[1-9]|1[0-4]|1[7-9]|20|geschichtsstadt|schlosshalde)\.jpg$#', $value)) {
        return $value;
    }
    if (preg_match('#^data/uploads/(sammlung|lindengut|moersburg)-[1-6]-[a-z0-9]+\.(jpe?g|png|webp)$#', $value)) {
        return $value;
    }
    if (preg_match('#^data/uploads/rueckblick-([1-9]|[1-3][0-9]|4[0-8])-[a-z0-9]+\.(jpe?g|png|webp)$#', $value)) {
        return $value;
    }
    if (preg_match('#^data/uploads/(partnerlogo|partnerbild)-(?:[1-9]|1[0-9]|20)-[a-z0-9]+\.(jpe?g|png|webp)$#', $value)) {
        return $value;
    }
    return '';
}

function hvw_image_info(string $id): ?array
{
    if (preg_match('/^agenda\.rueckblick\.([1-9]|[1-3][0-9]|4[0-8])\.image$/', $id, $m)) {
        return ['prefix' => 'rueckblick', 'slot' => (int) $m[1]];
    }
    if (preg_match('/^sammlung\.objekt\.([1-6])\.image$/', $id, $m)) {
        return ['prefix' => 'sammlung', 'slot' => (int) $m[1]];
    }
    if (preg_match('/^(lindengut|moersburg)\.bild\.([1-3])\.image$/', $id, $m)) {
        return ['prefix' => $m[1], 'slot' => (int) $m[2]];
    }
    if (preg_match('/^partner\.([1-9]|1[0-9]|20)\.image$/', $id, $m)) {
        return [
            'prefix' => 'partnerbild',
            'slot' => (int) $m[1],
            'mode' => 'cover',
        ];
    }
    return null;
}

function hvw_image_filename(array $slotInfo): string
{
    $prefix = (string) ($slotInfo['prefix'] ?? '');
    $slot = (int) ($slotInfo['slot'] ?? 0);
    $maxSlot = 6;
    if (str_starts_with($prefix, 'partner')) {
        $maxSlot = 20;
    } elseif ($prefix === 'rueckblick') {
        $maxSlot = hvw_rueckblick_max();
    }
    if (!preg_match('/^(rueckblick|sammlung|lindengut|moersburg|partnerlogo|partnerbild)$/', $prefix) || $slot < 1 || $slot > $maxSlot) {
        return '';
    }
    return $prefix . '-' . $slot . '-' . bin2hex(random_bytes(4)) . '.jpg';
}

function hvw_image_slot(string $id): ?int
{
    $info = hvw_image_info($id);
    return $info['slot'] ?? null;
}

function hvw_image_public_url(string $rel): string
{
    $rel = ltrim(str_replace('\\', '/', $rel), '/');
    return $rel;
}

/** Öffentliches /data/ neben dem Bearbeitungszugang (/edit/). */
function hvw_public_data_dir(): ?string
{
    $dir = dirname(HVW_ROOT) . '/data';
    if (!is_dir($dir) || !is_writable($dir)) {
        return null;
    }
    return $dir;
}

function hvw_public_uploads_dir(): ?string
{
    $data = hvw_public_data_dir();
    if ($data === null) {
        return null;
    }
    $uploads = $data . '/uploads';
    if (!is_dir($uploads) && !mkdir($uploads, 0775, true) && !is_dir($uploads)) {
        return null;
    }
    if (!is_writable($uploads)) {
        return null;
    }
    return $uploads;
}

function hvw_upload_basename(string $rel): string
{
    $rel = str_replace('\\', '/', $rel);
    if (!preg_match('#^data/uploads/([^/]+)$#', $rel, $m)) {
        return '';
    }
    $base = basename($m[1]);
    return $base === $m[1] ? $base : '';
}

/** Kopiert eine Datei aus /edit/data/uploads/ ins öffentliche /data/uploads/. */
function hvw_mirror_upload_to_public(string $basename): bool
{
    if ($basename === '' || str_contains($basename, '/') || str_contains($basename, '..')) {
        return false;
    }
    $src = HVW_UPLOADS . '/' . $basename;
    if (!is_file($src)) {
        return false;
    }
    $destDir = hvw_public_uploads_dir();
    if ($destDir === null) {
        return false;
    }
    return copy($src, $destDir . '/' . $basename);
}

/** Alle in Feldern referenzierten Upload-Bilder für die Live-Seite spiegeln. */
function hvw_sync_field_uploads_to_public(array $fields): void
{
    foreach ($fields as $value) {
        if (!is_string($value) || $value === '') {
            continue;
        }
        $path = hvw_sanitize_image_path($value);
        if ($path === '' || !str_starts_with($path, 'data/uploads/')) {
            continue;
        }
        $base = hvw_upload_basename($path);
        if ($base !== '') {
            hvw_mirror_upload_to_public($base);
        }
    }
}

function hvw_seed_fields(): array
{
    $path = HVW_ROOT . '/data/content-live.seed.json';
    if (!is_file($path)) {
        $path = HVW_LIVE;
    }
    $data = hvw_read_json($path);
    $fields = $data['fields'] ?? [];
    return is_array($fields) ? $fields : [];
}

function hvw_fallback_fields(): array
{
    $live = hvw_live()['fields'] ?? [];
    $draft = [];
    if (is_file(HVW_DRAFT)) {
        $draft = hvw_read_json(HVW_DRAFT)['fields'] ?? [];
    }
    $draft = is_array($draft) ? $draft : [];
    $live = is_array($live) ? $live : [];
    return array_merge(hvw_seed_fields(), $live, $draft);
}

function hvw_normalize_fields(array $incoming, ?array $fallback = null): array
{
    $schema = hvw_extend_schema_from_fields(hvw_schema(), $incoming);
    $fallback = $fallback ?? hvw_fallback_fields();
    $out = [];
    $errors = [];
    foreach ($schema as $id => $meta) {
        if (!array_key_exists($id, $incoming)) {
            if (array_key_exists($id, $fallback)) {
                $incoming[$id] = $fallback[$id];
            } else {
                $errors[] = 'Feld fehlt: ' . $id;
                continue;
            }
        }
        $raw = (string) $incoming[$id];
        $rich = !empty($meta['rich']);
        if (hvw_is_image_field($meta)) {
            $value = hvw_sanitize_image_path($raw);
            if ($raw !== '' && $value === '') {
                $errors[] = ($meta['label'] ?? $id) . ' hat einen ungültigen Bildpfad.';
            }
        } elseif (hvw_is_url_field($meta)) {
            $value = hvw_sanitize_url($raw);
            if ($raw !== '' && $value === '') {
                $errors[] = ($meta['label'] ?? $id) . ' hat eine ungültige Webadresse.';
            }
        } else {
            $value = $rich ? hvw_sanitize_rich($raw) : hvw_sanitize_plain($raw);
        }
        $len = hvw_plain_len($value);
        $max = (int) ($meta['max'] ?? 400);
        if ($len < 1 && !hvw_is_optional_field($meta)) {
            $errors[] = ($meta['label'] ?? $id) . ' darf nicht leer sein.';
        } elseif ($len > $max) {
            $errors[] = ($meta['label'] ?? $id) . " ist zu lang ({$len} von {$max} Zeichen).";
        }
        $out[$id] = $value;
    }
    if ($errors) {
        hvw_json(['ok' => false, 'error' => implode(' ', $errors), 'errors' => $errors], 422);
    }
    return $out;
}

function hvw_live(): array
{
    $data = hvw_read_json(HVW_LIVE);
    $data['fields'] = is_array($data['fields'] ?? null) ? $data['fields'] : [];
    return $data;
}

function hvw_draft(): array
{
    if (!is_file(HVW_DRAFT)) {
        $live = hvw_live();
        $live['status'] = 'clean';
        return $live;
    }
    $data = hvw_read_json(HVW_DRAFT);
    $data['fields'] = is_array($data['fields'] ?? null) ? $data['fields'] : [];
    return $data;
}

function hvw_norm_text(string $value): string
{
    $collapsed = preg_replace('/\s+/u', ' ', $value);
    return trim(is_string($collapsed) ? $collapsed : $value);
}

function hvw_comparable_field(string $value, array $meta): string
{
    if (hvw_is_image_field($meta)) {
        return trim($value);
    }
    if (!empty($meta['rich'])) {
        return hvw_norm_text(hvw_sanitize_rich($value));
    }
    return hvw_norm_text($value);
}

function hvw_diff(array $draftFields, array $liveFields): array
{
    $schema = hvw_schema();
    $changes = [];
    foreach ($schema as $id => $meta) {
        $a = (string) ($liveFields[$id] ?? '');
        if (!array_key_exists($id, $draftFields)) {
            continue;
        }
        $b = (string) $draftFields[$id];
        if (hvw_comparable_field($a, $meta) !== hvw_comparable_field($b, $meta)) {
            $changes[] = [
                'id' => $id,
                'label' => $meta['label'] ?? $id,
                'page' => $meta['page'] ?? '',
                'live' => $a,
                'draft' => $b,
            ];
        }
    }
    return $changes;
}
