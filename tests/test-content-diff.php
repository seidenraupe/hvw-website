<?php
declare(strict_types=1);

require_once dirname(__DIR__) . '/redaktion/lib.php';

$live = hvw_live()['fields'];
$draftMissingNew = $live;
foreach (array_keys($live) as $id) {
    if (
        str_starts_with($id, 'agenda.')
        || str_starts_with($id, 'mitmachen.')
        || str_starts_with($id, 'partner.')
        || str_starts_with($id, 'sammlung.')
        || str_starts_with($id, 'zitate.')
    ) {
        unset($draftMissingNew[$id]);
    }
}

$changes = hvw_diff($draftMissingNew, $live);
foreach ($changes as $change) {
    if (
        str_starts_with($change['id'], 'agenda.')
        || str_starts_with($change['id'], 'mitmachen.')
        || str_starts_with($change['id'], 'partner.')
        || str_starts_with($change['id'], 'sammlung.')
        || str_starts_with($change['id'], 'zitate.')
    ) {
        fwrite(STDERR, "Neue Felder dürfen ohne Entwurf nicht als Änderung gelten: {$change['id']}\n");
        exit(1);
    }
}

$draftEdited = $draftMissingNew;
$draftEdited['ueber-uns.intro'] = 'Heute überarbeiteter Einleitungstext für den Test.';
$changes = hvw_diff($draftEdited, $live);
$ids = array_column($changes, 'id');
if (!in_array('ueber-uns.intro', $ids, true)) {
    fwrite(STDERR, "Echte Entwurfsänderung an ueber-uns.intro muss sichtbar bleiben.\n");
    exit(1);
}

$draftWhitespace = $live;
$draftWhitespace['agenda.intro'] = "  " . $live['agenda.intro'] . "\n";
$changes = hvw_diff($draftWhitespace, $live);
$ids = array_column($changes, 'id');
if (in_array('agenda.intro', $ids, true)) {
    fwrite(STDERR, "Nur-Leerzeichen am neuen Feld darf keine Änderung sein.\n");
    exit(1);
}

$liveLinks = [
    'moersburg.oeffnung' => 'Regelmässige <a href="dokumente/szenische-fuehrung-berta.pdf">öffentliche Führungen</a>.',
];
$draftLinks = [
    'moersburg.oeffnung' => 'Regelmässige <a href="dokumente/szenische-fuehrung-berta.pdf" target="_blank" rel="noopener noreferrer">öffentliche Führungen</a>.',
];
$changes = hvw_diff($draftLinks, $liveLinks);
$ids = array_column($changes, 'id');
if (in_array('moersburg.oeffnung', $ids, true)) {
    fwrite(STDERR, "Dieselbe Führungs-Verlinkung darf nicht erneut zur Freigabe erscheinen.\n");
    exit(1);
}

$draftBold = ['ueber-uns.vorstand.person1' => '<b>Christian Huggenberg</b> — Präsident und Mitglied Leitungsteam Museum Schaffen'];
$liveBold = ['ueber-uns.vorstand.person1' => '<strong>Christian Huggenberg</strong> — Präsident und Mitglied Leitungsteam Museum Schaffen'];
$changes = hvw_diff($draftBold, $liveBold);
$ids = array_column($changes, 'id');
if (in_array('ueber-uns.vorstand.person1', $ids, true)) {
    fwrite(STDERR, "Fett als b oder strong darf keine neue Freigabe auslösen.\n");
    exit(1);
}

$draftReal = $draftLinks;
$draftReal['moersburg.oeffnung'] = 'Regelmässige <a href="dokumente/szenische-fuehrung-berta.pdf">geänderte Führungen</a>.';
$changes = hvw_diff($draftReal, $liveLinks);
$ids = array_column($changes, 'id');
if (!in_array('moersburg.oeffnung', $ids, true)) {
    fwrite(STDERR, "Geänderter Linktext muss zur Freigabe bleiben.\n");
    exit(1);
}

echo "content diff ok\n";
