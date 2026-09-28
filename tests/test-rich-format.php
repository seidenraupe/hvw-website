<?php
declare(strict_types=1);

require_once dirname(__DIR__) . '/redaktion/lib.php';

function assert_same(string $actual, string $expected, string $label): void
{
    if ($actual !== $expected) {
        fwrite(STDERR, $label . "\n  ist:  " . $actual . "\n  soll: " . $expected . "\n");
        exit(1);
    }
}

function assert_true(bool $ok, string $label): void
{
    if (!$ok) {
        fwrite(STDERR, $label . "\n");
        exit(1);
    }
}

assert_same(hvw_sanitize_rich('<b>fett</b>'), '<strong>fett</strong>', 'b wird zu strong');
assert_same(hvw_sanitize_rich('<i class="x">kursiv</i>'), '<em>kursiv</em>', 'i wird zu em');
assert_same(hvw_sanitize_rich('<u onclick="x">unter</u>'), '<u>unter</u>', 'u bleibt, Attribute weg');
assert_same(hvw_sanitize_rich('<b><i>beides</i></b>'), '<strong><em>beides</em></strong>', 'verschachtelt');
assert_same(
    hvw_sanitize_rich('Bürgerhaus <b>Lindengut</b>'),
    'Bürgerhaus <strong>Lindengut</strong>',
    'Umlaute bleiben'
);

$agenda = hvw_sanitize_rich('<a href="agenda.html" onclick="alert(1)">Agenda</a>');
assert_same($agenda, '<a href="agenda.html">Agenda</a>', 'interner Link');

$extern = hvw_sanitize_rich('<a href="https://example.com/seite">Extern</a>');
assert_true(str_contains($extern, 'href="https://example.com/seite"'), 'externer Link bleibt');
assert_true(str_contains($extern, 'target="_blank"'), 'externer Link öffnet neu');
assert_true(str_contains($extern, 'rel="noopener noreferrer"'), 'externer Link ohne Referrer');
assert_true(!str_contains($extern, 'onclick'), 'onclick am Link weg');

$js = hvw_sanitize_rich('<a href="javascript:alert(1)">Klick</a>');
assert_same($js, 'Klick', 'javascript-Link wird entpackt');

$script = hvw_sanitize_rich('Text<script>alert(1)</script>');
assert_true(!str_contains($script, 'script') && !str_contains($script, 'alert'), 'script wird entfernt');

$span = hvw_sanitize_rich('<span style="font-weight: bold">Span</span>');
assert_same($span, '<strong>Span</strong>', 'span font-weight wird strong');

echo "rich format ok\n";
