# Dependency-Sicherheitsstand (26.10.2026)

Die wiederhergestellte Next.js-App wurde auf die von Vercel am 14. Oktober 2026 empfohlene Maintenance-LTS-Version **Next.js 15.5.28** aktualisiert. Vercel nennt 15.5.28 als gepatchte 15.x-Version für den SVG-Image-Optimization-RCE und den App-Router-DoS in Server Actions. Die Doku empfiehlt ein zeitnahes Update auch dann, wenn eine App nicht alle betroffenen Funktionen nutzt.[1]

Der durch Next.js gebundene PostCSS-Stand war zusätzlich von mehreren Advisorys betroffen. Der Lockfile-Override hebt PostCSS auf **8.5.31**; damit meldet `npm audit` für das installierte JavaScript-Abhängigkeitsdiagramm am Prüfdatum **null** bekannte Advisories. Das ist kein allgemeiner Sicherheitsnachweis für Betriebssystem, Deployment, andere Pakete oder spätere Änderungen.[2]

Ein Upgrade auf Next.js 16 wurde nicht erzwungen. Die offizielle Migrationsanleitung nennt unter anderem Node.js 20.9+ und Änderungen an synchronem Zugriff auf Request-APIs. Der lokale Build und TypeScript-Check müssen nach den gerade eingespielten Änderungen noch durchgeführt werden.[3]

## Reproduzierbare Angaben

- Next.js: 15.5.28
- PostCSS: 8.5.31 über `overrides` in `package.json`
- `@celo/attribution-tags`: 0.5.0
- Viem: 2.57.3
- `npm audit`: 0 Advisories zum Stichtag
- Noch keine GitHub-Veröffentlichung, kein Deployment und keine On-chain-Transaktion aus dieser Arbeitskopie

## References

[1]: https://nextjs.org/blog/nextjs-security-update-october-14-2026 "Next.js Security Update for Upstream Vulnerabilities"
[2]: https://github.com/advisories/GHSA-fxqj-rqcc-2cmp "PostCSS arbitrary file disclosure in previous source maps"
[3]: https://nextjs.org/docs/app/guides/upgrading/version-16 "Next.js version 16 upgrade guide"
