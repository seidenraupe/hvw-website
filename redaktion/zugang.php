<?php
declare(strict_types=1);

require_once dirname(__DIR__) . '/zugang/lib.php';
hvw_boot_session();

$user = hvw_user();
if (!$user) {
    header('Location: index.php?next=' . rawurlencode('zugang.php'), true, 302);
    exit;
}
if ($user['role'] !== 'freigabe') {
    http_response_code(403);
}

$error = '';
$notice = '';

if ($user['role'] === 'freigabe' && ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
    if (!hash_equals((string) ($_SESSION['csrf'] ?? ''), (string) ($_POST['csrf'] ?? ''))) {
        $error = 'Sitzung abgelaufen. Bitte neu laden.';
    } else {
        $emails = hvw_access_emails();
        $action = (string) ($_POST['action'] ?? '');
        if ($action === 'add') {
            $n = hvw_normalize_email((string) ($_POST['email'] ?? ''));
            if (!filter_var($n, FILTER_VALIDATE_EMAIL)) {
                $error = 'Bitte eine gültige E-Mail-Adresse eingeben.';
            } elseif (in_array($n, $emails, true)) {
                $error = 'Diese Adresse ist bereits eingetragen.';
            } else {
                $emails[] = $n;
                hvw_write_access_emails($emails);
                $notice = 'Adresse hinzugefügt. Die Person kann sich auf der Vorschau einen Code senden lassen.';
            }
        } elseif ($action === 'remove') {
            $n = hvw_normalize_email((string) ($_POST['email'] ?? ''));
            $emails = array_values(array_filter($emails, static fn ($e) => $e !== $n));
            hvw_write_access_emails($emails);
            $notice = 'Adresse entfernt.';
        }
    }
}

$emails = hvw_access_emails();
$esc = static fn (string $s): string => htmlspecialchars($s, ENT_QUOTES, 'UTF-8');
?>
<!DOCTYPE html>
<html lang="de-CH">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Zugang Vorschau — Historischer Verein Winterthur</title>
  <meta name="robots" content="noindex,nofollow">
  <link rel="icon" href="../images/favicon.ico" sizes="any">
  <link rel="stylesheet" href="../css/fonts.css">
  <link rel="stylesheet" href="../css/tailwind.css">
  <link rel="stylesheet" href="../css/site.css">
</head>
<body class="bg-hvw-fog font-sans text-hvw-ink antialiased">
  <main class="mx-auto max-w-xl px-5 py-12">
    <p class="text-sm font-semibold uppercase tracking-[0.08em] text-hvw-mute">Änderungsmodus</p>
    <h1 class="mt-2 text-3xl font-semibold">Zugelassene E-Mail-Adressen</h1>
    <p class="mt-3 text-hvw-mute">
      Wer hier steht, kann auf der Vorschau einen Code per Mail anfordern und danach die Seiten ansehen.
      Texte ändern weiterhin nur <strong>Redaktion</strong> und <strong>Freigabe</strong> mit ihrem Login.
    </p>
    <p class="mt-4">
      <a href="../index.html" class="underline underline-offset-2">Zur Vorschau</a>
      ·
      <a href="index.php" class="underline underline-offset-2">Redaktions-Login</a>
    </p>

    <?php if ($user['role'] !== 'freigabe'): ?>
      <p class="mt-8 border border-hvw-ink bg-white px-5 py-4">Nur die Rolle Freigabe darf Adressen ändern. Sie sind als <?php echo $esc($user['name']); ?> angemeldet.</p>
    <?php endif; ?>

    <?php if ($error): ?>
      <p class="mt-6 border border-red-700 bg-red-50 px-4 py-3 text-red-800" role="alert"><?php echo $esc($error); ?></p>
    <?php endif; ?>
    <?php if ($notice): ?>
      <p class="mt-6 border border-hvw-ink bg-white px-4 py-3"><?php echo $esc($notice); ?></p>
    <?php endif; ?>

    <ul class="mt-8 border border-hvw-ink bg-white">
      <?php if (!$emails): ?>
        <li class="px-5 py-4 text-hvw-mute">Noch keine Adressen. Beim ersten Aufruf der Vorschau werden die drei HVW-Adressen eingetragen.</li>
      <?php endif; ?>
      <?php foreach ($emails as $item): ?>
        <li class="flex flex-wrap items-center justify-between gap-3 border-b border-hvw-ink/15 px-5 py-3 last:border-b-0">
          <span><?php echo $esc($item); ?></span>
          <?php if ($user['role'] === 'freigabe'): ?>
            <form method="post">
              <input type="hidden" name="csrf" value="<?php echo $esc((string) ($_SESSION['csrf'] ?? '')); ?>">
              <input type="hidden" name="action" value="remove">
              <input type="hidden" name="email" value="<?php echo $esc($item); ?>">
              <button type="submit" class="min-h-11 border border-hvw-ink px-3 font-semibold hover:bg-hvw-fog">Entfernen</button>
            </form>
          <?php endif; ?>
        </li>
      <?php endforeach; ?>
    </ul>

    <?php if ($user['role'] === 'freigabe'): ?>
      <form method="post" class="mt-8 border border-hvw-ink bg-white p-6">
        <input type="hidden" name="csrf" value="<?php echo $esc((string) ($_SESSION['csrf'] ?? '')); ?>">
        <input type="hidden" name="action" value="add">
        <label class="block text-sm font-semibold" for="email">Neue E-Mail-Adresse</label>
        <input class="mt-2 min-h-12 w-full border border-hvw-ink px-4 text-base" id="email" name="email" type="email" required autocomplete="email">
        <button type="submit" class="mt-6 min-h-12 w-full bg-hvw-ink font-semibold text-white hover:bg-hvw-charcoal">Hinzufügen</button>
      </form>
    <?php endif; ?>
  </main>
</body>
</html>
