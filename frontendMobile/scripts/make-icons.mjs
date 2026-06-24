// Render the app icon + splash source images (assets/*.png) from inline SVG, using
// sharp (bundled with @capacitor/assets). Run once; commit the PNGs. The build then
// turns them into Android densities via `capacitor-assets generate --android`.
//
//   node scripts/make-icons.mjs
//
// Design: a white open Muṣḥaf (Qur'an) on the dark-green brand background.

import sharp from 'sharp';
import { mkdirSync } from 'node:fs';

mkdirSync('assets', { recursive: true });

const book = `
  <path d="M512 392 C 430 350 330 350 268 374 C 252 380 244 394 244 410 V 660 C 244 676 256 688 272 686 C 360 676 452 690 512 718 Z" fill="#ffffff"/>
  <path d="M512 392 C 594 350 694 350 756 374 C 772 380 780 394 780 410 V 660 C 780 676 768 688 752 686 C 664 676 572 690 512 718 Z" fill="#ffffff"/>
  <path d="M512 392 V 718" stroke="#bfe3d2" stroke-width="12" stroke-linecap="round"/>
  <g stroke="#2a7d5d" stroke-width="15" stroke-linecap="round" opacity="0.5">
    <path d="M316 452 H468"/><path d="M300 508 H468"/><path d="M300 562 H468"/><path d="M300 616 H448"/>
    <path d="M556 452 H708"/><path d="M556 508 H724"/><path d="M556 562 H724"/><path d="M576 616 H724"/>
  </g>`;

const defs = `<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#1c5e44"/><stop offset="1" stop-color="#0f3d2b"/></linearGradient></defs>`;

const doc = (inner, size) =>
	`<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">${inner}</svg>`;

const bg = doc(`${defs}<rect width="1024" height="1024" fill="url(#g)"/>`, 1024);
const fg = doc(book, 1024);
const full = doc(`${defs}<rect width="1024" height="1024" fill="url(#g)"/>${book}`, 1024);
const splash = doc(
	`${defs}<rect width="2732" height="2732" fill="url(#g)"/>
   <g transform="translate(1366 1366) scale(1.6) translate(-512 -512)">${book}</g>`,
	2732
);

const png = (svg) => sharp(Buffer.from(svg)).png();

await png(bg).toFile('assets/icon-background.png');
await png(fg).toFile('assets/icon-foreground.png');
await png(full).toFile('assets/icon-only.png');
await png(splash).toFile('assets/splash.png');
await png(splash).toFile('assets/splash-dark.png');

console.log('Rendered assets/: icon-only, icon-foreground, icon-background, splash, splash-dark');
