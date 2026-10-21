<?php
/**
 * E-Mail-Versand für den Redaktions-Modus (/edit/).
 * Wird beim Deploy aus GitHub-Secrets erzeugt (config.mail.php) oder manuell kopiert.
 *
 * Microsoft 365 (Postfach noreply@hvwinterthur.ch):
 *
 * return [
 *   'host' => 'smtp.office365.com',
 *   'port' => 587,
 *   'user' => 'noreply@hvwinterthur.ch',
 *   'pass' => '…',
 *   'secure' => 'tls',
 *   'from' => 'noreply@hvwinterthur.ch',
 *   'from_name' => 'Historischer Verein Winterthur',
 *   'allowed_emails' => [
 *     'thomas.giger@hvwinterthur.ch',
 *     'christian.huggenberg@hvwinterthur.ch',
 *     'gioia.joehri@hvwinterthur.ch',
 *   ],
 * ];
 */
