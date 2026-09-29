<?php
require dirname(__DIR__) . '/redaktion/lib.php';

$ok = hvw_sanitize_image_path('data/uploads/rueckblick-3-ab12cd34.jpg');
if ($ok !== 'data/uploads/rueckblick-3-ab12cd34.jpg') {
    fwrite(STDERR, "gültiger Upload-Pfad wurde verworfen\n");
    exit(1);
}
if (hvw_sanitize_image_path('../etc/passwd') !== '') {
    fwrite(STDERR, "Pfadtraversal nicht blockiert\n");
    exit(1);
}
if (hvw_sanitize_image_path('https://evil.example/x.jpg') !== '') {
    fwrite(STDERR, "externe URL nicht blockiert\n");
    exit(1);
}
if (hvw_sanitize_image_path('images/placeholder-event-2.svg') !== 'images/placeholder-event-2.svg') {
    fwrite(STDERR, "Platzhalter muss erlaubt bleiben\n");
    exit(1);
}
if (hvw_image_slot('agenda.rueckblick.4.image') !== 4) {
    fwrite(STDERR, "Slot-Erkennung fehlgeschlagen\n");
    exit(1);
}
if (hvw_image_slot('sammlung.objekt.2.image') !== 2) {
    fwrite(STDERR, "Sammlung-Slot fehlgeschlagen\n");
    exit(1);
}
$info = hvw_image_info('sammlung.objekt.5.image');
if (!$info || $info['prefix'] !== 'sammlung' || $info['slot'] !== 5) {
    fwrite(STDERR, "Sammlung image-info fehlgeschlagen\n");
    exit(1);
}
if (hvw_sanitize_image_path('data/uploads/sammlung-1-aabbccdd.jpg') !== 'data/uploads/sammlung-1-aabbccdd.jpg') {
    fwrite(STDERR, "Sammlung-Upload-Pfad wurde verworfen\n");
    exit(1);
}
if (hvw_sanitize_image_path('images/sammlung-ausstellung.jpg') !== 'images/sammlung-ausstellung.jpg') {
    fwrite(STDERR, "Sammlungs-Startbild muss erlaubt bleiben\n");
    exit(1);
}
if (hvw_image_slot('agenda.rueckblick.1.title') !== null) {
    fwrite(STDERR, "Titel darf kein Bild-Slot sein\n");
    exit(1);
}

$schema = hvw_schema();
$incoming = [];
foreach ($schema as $id => $meta) {
    if (!empty($meta['type']) && $meta['type'] === 'image') {
        $incoming[$id] = '';
    } elseif (($meta['type'] ?? '') === 'url') {
        $incoming[$id] = 'https://www.hvwinterthur.ch/';
    } else {
        $incoming[$id] = 'Test';
    }
}
$incoming['agenda.rueckblick.1.image'] = 'data/uploads/rueckblick-1-aabbccdd.jpg';
$normalized = hvw_normalize_fields($incoming, $incoming);
if ($normalized['agenda.rueckblick.1.image'] !== 'data/uploads/rueckblick-1-aabbccdd.jpg') {
    fwrite(STDERR, "Normalize hat Bildpfad verloren\n");
    exit(1);
}
if ($normalized['agenda.rueckblick.2.image'] !== '') {
    fwrite(STDERR, "leeres optionales Bild muss leer bleiben\n");
    exit(1);
}

$generated = hvw_image_filename(['prefix' => 'sammlung', 'slot' => 3]);
if (!preg_match('#^sammlung-3-[a-z0-9]+\.jpg$#', $generated)) {
    fwrite(STDERR, "Dateiname für Sammlung-Upload ist falsch: {$generated}\n");
    exit(1);
}
if (hvw_sanitize_image_path('data/uploads/' . $generated) !== 'data/uploads/' . $generated) {
    fwrite(STDERR, "erzeugter Sammlung-Pfad wurde als ungültig abgelehnt\n");
    exit(1);
}
if (hvw_image_filename(['mime' => 'image/jpeg', 0 => 1200, 1 => 900]) !== '') {
    fwrite(STDERR, "getimagesize-Array darf keinen Dateinamen erzeugen\n");
    exit(1);
}
if (hvw_sanitize_image_path('data/uploads/--aabbccdd.jpg') !== '') {
    fwrite(STDERR, "kaputter Upload-Name --hex.jpg muss abgelehnt werden\n");
    exit(1);
}

$incoming['sammlung.objekt.1.body'] = str_repeat('a', 400);
$normalized = hvw_normalize_fields($incoming, $incoming);
if (strlen($normalized['sammlung.objekt.1.body']) !== 400) {
    fwrite(STDERR, "400 Zeichen Sammlungstext wurden nicht übernommen\n");
    exit(1);
}

$info = hvw_image_info('lindengut.bild.2.image');
if (!$info || $info['prefix'] !== 'lindengut' || $info['slot'] !== 2) {
    fwrite(STDERR, "Lindengut-Bildfeld nicht erkannt\n");
    exit(1);
}
$generatedMuseum = hvw_image_filename($info);
if (!preg_match('#^lindengut-2-[a-z0-9]+\.jpg$#', $generatedMuseum)) {
    fwrite(STDERR, "Lindengut-Dateiname falsch: {$generatedMuseum}\n");
    exit(1);
}
if (hvw_sanitize_image_path('data/uploads/' . $generatedMuseum) !== 'data/uploads/' . $generatedMuseum) {
    fwrite(STDERR, "Lindengut-Upload-Pfad abgelehnt\n");
    exit(1);
}

$partner = hvw_image_info('partner.10.image');
if (!$partner || $partner['prefix'] !== 'partnerbild' || $partner['slot'] !== 10 || ($partner['mode'] ?? '') !== 'cover') {
    fwrite(STDERR, "Partner-Bild nicht erkannt\n");
    exit(1);
}
$partnerName = hvw_image_filename($partner);
if (!preg_match('#^partnerbild-10-[a-z0-9]+\.jpg$#', $partnerName)) {
    fwrite(STDERR, "Partner-Dateiname falsch: {$partnerName}\n");
    exit(1);
}
if (hvw_sanitize_image_path('data/uploads/' . $partnerName) !== 'data/uploads/' . $partnerName) {
    fwrite(STDERR, "Partner-Upload-Pfad abgelehnt\n");
    exit(1);
}
$geschichtsstadt = hvw_image_info('partner.15.image');
if (!$geschichtsstadt || $geschichtsstadt['prefix'] !== 'partnerbild' || $geschichtsstadt['slot'] !== 15) {
    fwrite(STDERR, "Partner 15 nicht erkannt\n");
    exit(1);
}
if (hvw_sanitize_image_path('images/partner/hero-20.jpg') !== 'images/partner/hero-20.jpg') {
    fwrite(STDERR, "Heimatschutz-Hero muss erlaubt bleiben\n");
    exit(1);
}
$heimat = hvw_image_info('partner.20.image');
if (!$heimat || $heimat['prefix'] !== 'partnerbild' || $heimat['slot'] !== 20) {
    fwrite(STDERR, "Partner 20 nicht erkannt\n");
    exit(1);
}
if (hvw_sanitize_image_path('images/partner/hero-16.jpg') !== '') {
    fwrite(STDERR, "unbekannter Partner-Hero wurde durchgelassen\n");
    exit(1);
}
if (hvw_sanitize_url('https://dorfmuseum-wülflingen.ch/') !== 'https://dorfmuseum-wülflingen.ch/') {
    fwrite(STDERR, "Partner-URL mit Umlaut wurde verworfen\n");
    exit(1);
}
if (hvw_sanitize_url('javascript:alert(1)') !== '' || hvw_sanitize_url('http://example.com') !== '') {
    fwrite(STDERR, "unsichere URL wurde durchgelassen\n");
    exit(1);
}

echo "image fields php ok\n";
