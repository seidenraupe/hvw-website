<?php
declare(strict_types=1);

require_once __DIR__ . '/lib.php';

hvw_boot_session();

$action = $_GET['action'] ?? $_POST['action'] ?? '';
$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';

if ($action === 'me' && $method === 'GET') {
    $user = hvw_user();
    hvw_json(['ok' => true, 'user' => $user]);
}

if ($action === 'schema' && $method === 'GET') {
    hvw_json(['ok' => true, 'fields' => hvw_schema()]);
}

if ($action === 'login' && $method === 'POST') {
    $body = json_decode((string) file_get_contents('php://input'), true);
    if (!is_array($body)) {
        $body = $_POST;
    }
    $id = trim((string) ($body['username'] ?? ''));
    $password = (string) ($body['password'] ?? '');
    $users = hvw_users();
    if (!isset($users[$id]) || !password_verify($password, $users[$id]['hash'])) {
        usleep(250000);
        hvw_json(['ok' => false, 'error' => 'Benutzername oder Passwort stimmt nicht.'], 401);
    }
    session_regenerate_id(true);
    $_SESSION['user'] = $id;
    $_SESSION['csrf'] = bin2hex(random_bytes(16));
    hvw_json(['ok' => true, 'user' => hvw_user()]);
}

if ($action === 'logout' && $method === 'POST') {
    hvw_require_csrf();
    $_SESSION = [];
    if (ini_get('session.use_cookies')) {
        $p = session_get_cookie_params();
        setcookie(session_name(), '', time() - 42000, $p['path'], $p['domain'] ?? '', (bool) $p['secure'], (bool) $p['httponly']);
    }
    session_destroy();
    hvw_json(['ok' => true]);
}

if ($action === 'content' && $method === 'GET') {
    $source = $_GET['source'] ?? 'live';
    if ($source === 'draft') {
        $user = hvw_require_user();
        $draft = hvw_draft();
        $live = hvw_live();
        hvw_json([
            'ok' => true,
            'source' => 'draft',
            'role' => $user['role'],
            'updatedAt' => $draft['updatedAt'] ?? null,
            'updatedBy' => $draft['updatedBy'] ?? null,
            'fields' => $draft['fields'],
            'changes' => hvw_diff($draft['fields'], $live['fields']),
        ]);
    }
    $live = hvw_live();
    hvw_json([
        'ok' => true,
        'source' => 'live',
        'updatedAt' => $live['updatedAt'] ?? null,
        'updatedBy' => $live['updatedBy'] ?? null,
        'fields' => $live['fields'],
    ]);
}

if ($action === 'save' && $method === 'POST') {
    $user = hvw_require_user();
    hvw_require_csrf();
    $body = json_decode((string) file_get_contents('php://input'), true);
    if (!is_array($body) || !isset($body['fields']) || !is_array($body['fields'])) {
        hvw_json(['ok' => false, 'error' => 'Keine Texte empfangen.'], 400);
    }
    $fields = hvw_normalize_fields($body['fields']);
    $now = gmdate('Y-m-d\TH:i:s\Z');
    $draft = [
        'updatedAt' => $now,
        'updatedBy' => $user['id'],
        'status' => 'draft',
        'fields' => $fields,
    ];
    hvw_write_json(HVW_DRAFT, $draft);
    $live = hvw_live();
    hvw_json([
        'ok' => true,
        'updatedAt' => $now,
        'changes' => hvw_diff($fields, $live['fields']),
    ]);
}

if ($action === 'publish' && $method === 'POST') {
    $user = hvw_require_user();
    hvw_require_csrf();
    if ($user['role'] !== 'freigabe') {
        hvw_json(['ok' => false, 'error' => 'Nur die Freigabe-Rolle darf live schalten.'], 403);
    }
    $draft = hvw_draft();
    $fields = hvw_normalize_fields($draft['fields'] ?? []);
    $now = gmdate('Y-m-d\TH:i:s\Z');
    $live = [
        'updatedAt' => $now,
        'updatedBy' => $user['id'],
        'publishedFrom' => $draft['updatedAt'] ?? $now,
        'fields' => $fields,
    ];
    hvw_write_json(HVW_LIVE, $live);
    $publicLive = dirname(HVW_ROOT) . '/data/content-live.json';
    if (is_dir(dirname(HVW_ROOT) . '/data') && is_writable(dirname(HVW_ROOT) . '/data')) {
        hvw_write_json($publicLive, $live);
    }
    $draft['status'] = 'published';
    $draft['publishedAt'] = $now;
    $draft['fields'] = $fields;
    hvw_write_json(HVW_DRAFT, $draft);
    hvw_json(['ok' => true, 'updatedAt' => $now]);
}

if ($action === 'upload-image' && $method === 'POST') {
    $user = hvw_require_user();
    hvw_require_csrf();
    $fieldId = trim((string) ($_POST['field'] ?? ''));
    $schema = hvw_schema();
    $meta = $schema[$fieldId] ?? null;
    $slotInfo = hvw_image_info($fieldId);
    if (!$meta || !hvw_is_image_field($meta) || $slotInfo === null) {
        hvw_json(['ok' => false, 'error' => 'Dieses Feld nimmt kein Bild entgegen.'], 400);
    }
    if (empty($_FILES['file']) || !is_array($_FILES['file'])) {
        hvw_json(['ok' => false, 'error' => 'Bitte ein Bild auswählen.'], 400);
    }
    $file = $_FILES['file'];
    if ((int) ($file['error'] ?? UPLOAD_ERR_NO_FILE) !== UPLOAD_ERR_OK) {
        hvw_json(['ok' => false, 'error' => 'Das Bild konnte nicht hochgeladen werden.'], 400);
    }
    $size = (int) ($file['size'] ?? 0);
    if ($size < 32 || $size > 8 * 1024 * 1024) {
        hvw_json(['ok' => false, 'error' => 'Das Bild muss zwischen 1 KB und 8 MB liegen.'], 400);
    }
    $tmp = (string) ($file['tmp_name'] ?? '');
    if ($tmp === '' || !is_uploaded_file($tmp)) {
        hvw_json(['ok' => false, 'error' => 'Ungültige Datei.'], 400);
    }
    $imageSize = @getimagesize($tmp);
    if (!is_array($imageSize) || empty($imageSize[0]) || empty($imageSize[1])) {
        hvw_json(['ok' => false, 'error' => 'Nur JPG, PNG oder WebP sind erlaubt.'], 400);
    }
    $mime = (string) ($imageSize['mime'] ?? '');
    $src = null;
    if ($mime === 'image/jpeg' && function_exists('imagecreatefromjpeg')) {
        $src = @imagecreatefromjpeg($tmp);
    } elseif ($mime === 'image/png' && function_exists('imagecreatefrompng')) {
        $src = @imagecreatefrompng($tmp);
    } elseif ($mime === 'image/webp' && function_exists('imagecreatefromwebp')) {
        $src = @imagecreatefromwebp($tmp);
    }
    if (!$src) {
        hvw_json(['ok' => false, 'error' => 'Das Bildformat wird auf dem Server nicht unterstützt.'], 400);
    }

    $srcW = imagesx($src);
    $srcH = imagesy($src);
    $mode = (string) ($slotInfo['mode'] ?? 'cover');
    if ($mode === 'contain') {
        $targetW = 800;
        $targetH = 480;
        $dst = imagecreatetruecolor($targetW, $targetH);
        if ($dst === false) {
            imagedestroy($src);
            hvw_json(['ok' => false, 'error' => 'Bild konnte nicht verarbeitet werden.'], 500);
        }
        $white = imagecolorallocate($dst, 255, 255, 255);
        imagefilledrectangle($dst, 0, 0, $targetW, $targetH, $white);
        $scale = min($targetW / max(1, $srcW), $targetH / max(1, $srcH), 1);
        $dw = max(1, (int) round($srcW * $scale));
        $dh = max(1, (int) round($srcH * $scale));
        $dx = (int) floor(($targetW - $dw) / 2);
        $dy = (int) floor(($targetH - $dh) / 2);
        imagealphablending($dst, true);
        imagecopyresampled($dst, $src, $dx, $dy, 0, 0, $dw, $dh, $srcW, $srcH);
    } else {
        $targetW = 1200;
        $targetH = 900;
        $srcRatio = $srcW / max(1, $srcH);
        $targetRatio = $targetW / $targetH;
        if ($srcRatio > $targetRatio) {
            $cropH = $srcH;
            $cropW = (int) round($srcH * $targetRatio);
            $cropX = (int) floor(($srcW - $cropW) / 2);
            $cropY = 0;
        } else {
            $cropW = $srcW;
            $cropH = (int) round($srcW / $targetRatio);
            $cropX = 0;
            $cropY = (int) floor(($srcH - $cropH) / 2);
        }
        $dst = imagecreatetruecolor($targetW, $targetH);
        if ($dst === false) {
            imagedestroy($src);
            hvw_json(['ok' => false, 'error' => 'Bild konnte nicht verarbeitet werden.'], 500);
        }
        imagecopyresampled($dst, $src, 0, 0, $cropX, $cropY, $targetW, $targetH, $cropW, $cropH);
    }
    imagedestroy($src);

    if (!is_dir(HVW_UPLOADS) && !mkdir(HVW_UPLOADS, 0775, true) && !is_dir(HVW_UPLOADS)) {
        imagedestroy($dst);
        hvw_json(['ok' => false, 'error' => 'Upload-Ordner fehlt.'], 500);
    }
    $name = hvw_image_filename($slotInfo);
    if ($name === '') {
        imagedestroy($dst);
        hvw_json(['ok' => false, 'error' => 'Dieses Feld nimmt kein Bild entgegen.'], 400);
    }
    $abs = HVW_UPLOADS . '/' . $name;
    $ok = imagejpeg($dst, $abs, 86);
    imagedestroy($dst);
    if (!$ok || !is_file($abs)) {
        hvw_json(['ok' => false, 'error' => 'Das Bild konnte nicht gespeichert werden.'], 500);
    }

    $rel = 'data/uploads/' . $name;
    $draft = hvw_draft();
    $fields = is_array($draft['fields'] ?? null) ? $draft['fields'] : [];
    $fields[$fieldId] = $rel;
    $normalized = hvw_normalize_fields($fields);
    $now = gmdate('Y-m-d\TH:i:s\Z');
    $draft = [
        'updatedAt' => $now,
        'updatedBy' => $user['id'],
        'status' => 'draft',
        'fields' => $normalized,
    ];
    hvw_write_json(HVW_DRAFT, $draft);
    $live = hvw_live();
    hvw_json([
        'ok' => true,
        'field' => $fieldId,
        'url' => $rel,
        'updatedAt' => $now,
        'changes' => hvw_diff($normalized, $live['fields'] ?? []),
    ]);
}

if ($action === 'discard' && $method === 'POST') {
    $user = hvw_require_user();
    hvw_require_csrf();
    $live = hvw_live();
    $draft = [
        'updatedAt' => gmdate('Y-m-d\TH:i:s\Z'),
        'updatedBy' => $user['id'],
        'status' => 'discarded',
        'fields' => $live['fields'] ?? [],
    ];
    hvw_write_json(HVW_DRAFT, $draft);
    hvw_json(['ok' => true]);
}

hvw_json(['ok' => false, 'error' => 'Unbekannte Aktion.'], 404);
