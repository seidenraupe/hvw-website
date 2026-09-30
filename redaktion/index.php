<?php
declare(strict_types=1);

require_once __DIR__ . '/lib.php';
hvw_boot_session();

$user = hvw_user();
$error = '';

if (($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
    $id = trim((string) ($_POST['username'] ?? ''));
    $password = (string) ($_POST['password'] ?? '');
    $users = hvw_users();
    if (isset($users[$id]) && password_verify($password, $users[$id]['hash'])) {
        session_regenerate_id(true);
        $_SESSION['user'] = $id;
        $_SESSION['csrf'] = bin2hex(random_bytes(16));
        $next = (string) ($_POST['next'] ?? '../index.html');
        if ($next === '' || str_contains($next, '://') || str_starts_with($next, '//')) {
            $next = '../index.html';
        }
        header('Location: ' . $next, true, 302);
        exit;
    }
    usleep(250000);
    $error = 'Benutzername oder Passwort stimmt nicht.';
}

$next = (string) ($_GET['next'] ?? '../index.html');
if (str_contains($next, '://') || str_starts_with($next, '//')) {
    $next = '../index.html';
}
?>
<!DOCTYPE html>
<html lang="de-CH">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Redaktion — Historischer Verein Winterthur</title>
  <meta name="robots" content="noindex,nofollow">
  <link rel="icon" href="../images/favicon.ico" sizes="any">
  <link rel="stylesheet" href="../css/fonts.css">
  <link rel="stylesheet" href="../css/tailwind.css">
  <link rel="stylesheet" href="../css/site.css">
</head>
<body class="bg-hvw-fog font-sans text-hvw-ink antialiased">
  <main class="mx-auto flex min-h-screen max-w-md flex-col justify-center px-5 py-12">
    <p class="text-sm font-semibold uppercase tracking-[0.08em] text-hvw-mute">Historischer Verein Winterthur</p>
    <h1 class="mt-2 text-3xl font-semibold">Änderungsmodus</h1>
    <p class="mt-3 text-hvw-mute">
      Anmelden, auf der Website in einen Text klicken, speichern. Live geht nichts, bevor die Freigabe zustimmt.
    </p>

    <?php if ($user): ?>
      <p class="mt-6 border border-hvw-ink bg-white px-5 py-4">
        Sie sind angemeldet als <strong><?php echo htmlspecialchars($user['name'], ENT_QUOTES, 'UTF-8'); ?></strong>.
      </p>
      <p class="mt-4">
        <a href="../index.html" class="inline-flex min-h-12 items-center justify-center bg-hvw-ink px-5 font-semibold text-white no-underline hover:bg-hvw-charcoal">Zur Website</a>
      </p>
      <?php if ($user['role'] === 'freigabe'): ?>
      <p class="mt-3">
        <a href="zugang.php" class="inline-flex min-h-12 items-center justify-center border border-hvw-ink px-5 font-semibold no-underline hover:bg-hvw-fog">E-Mail-Zugang verwalten</a>
      </p>
      <?php endif; ?>
    <?php endif; ?>

    <form method="post" class="mt-8 border border-hvw-ink bg-white p-6">
      <input type="hidden" name="next" value="<?php echo htmlspecialchars($next, ENT_QUOTES, 'UTF-8'); ?>">
      <?php if ($error): ?>
        <p class="mb-4 border border-red-700 bg-red-50 px-4 py-3 text-red-800" role="alert"><?php echo htmlspecialchars($error, ENT_QUOTES, 'UTF-8'); ?></p>
      <?php endif; ?>
      <label class="block text-sm font-semibold" for="username">Benutzername</label>
      <input class="mt-2 min-h-12 w-full border border-hvw-ink px-4 text-base" id="username" name="username" required autocomplete="username">
      <label class="mt-4 block text-sm font-semibold" for="password">Passwort</label>
      <input class="mt-2 min-h-12 w-full border border-hvw-ink px-4 text-base" id="password" name="password" type="password" required autocomplete="current-password">
      <button type="submit" class="mt-6 min-h-12 w-full bg-hvw-ink font-semibold text-white hover:bg-hvw-charcoal">Anmelden</button>
    </form>
    <p class="mt-6 text-sm text-hvw-mute">
      Layout, Navigation und Agenda bleiben unverändert. Erlaubt in Texten: fett, kursiv, unterstrichen.
    </p>
  </main>
</body>
</html>
