#!/usr/bin/env php
<?php
/**
 * Einmalige Migration: config.local.php → nur Benutzer redaktion (role freigabe).
 *
 * Usage:
 *   php scripts/migrate-redaktion-config-local.php /pfad/edit/redaktion/config.local.php
 */
declare(strict_types=1);

$path = $argv[1] ?? '';
if ($path === '') {
    fwrite(STDERR, "Usage: php migrate-redaktion-config-local.php <config.local.php>\n");
    exit(1);
}

if (!is_file($path)) {
    echo "Keine config.local.php unter {$path} — es gelten die Defaults aus lib.php. Nichts zu tun.\n";
    exit(0);
}

$users = require $path;
if (!is_array($users)) {
    fwrite(STDERR, "config.local.php muss ein Array zurückgeben.\n");
    exit(1);
}

$needsMigration = isset($users['freigabe']);
if (isset($users['redaktion']) && ($users['redaktion']['role'] ?? '') !== 'freigabe') {
    $needsMigration = true;
}

if (!$needsMigration) {
    echo "Bereits migriert (nur redaktion mit role freigabe) — keine Änderung.\n";
    exit(0);
}

if (!isset($users['redaktion']) || !is_array($users['redaktion'])) {
    fwrite(STDERR, "Kein Benutzer «redaktion» in config.local.php — bitte manuell anpassen.\n");
    exit(1);
}

if (empty($users['redaktion']['hash'])) {
    fwrite(STDERR, "redaktion.hash fehlt — Migration abgebrochen.\n");
    exit(1);
}

$users['redaktion']['role'] = 'freigabe';
if (empty($users['redaktion']['name'])) {
    $users['redaktion']['name'] = 'Redaktion';
}
unset($users['freigabe']);

$backup = $path . '.bak-migrate-' . gmdate('Ymd-His');
if (!@copy($path, $backup)) {
    fwrite(STDERR, "Backup nach {$backup} fehlgeschlagen.\n");
    exit(1);
}

$content = "<?php\n/**\n * Migriert auf ein Redaktions-Login (" . gmdate('c') . " UTC)\n */\nreturn "
    . var_export($users, true) . ";\n";

if (@file_put_contents($path, $content) === false) {
    fwrite(STDERR, "Schreiben von {$path} fehlgeschlagen.\n");
    exit(1);
}

echo "Migration OK.\n";
echo "  Backup: {$backup}\n";
echo "  redaktion: role freigabe (Passwort-Hash unverändert)\n";
echo "  freigabe: entfernt\n";
exit(0);
