// The 114 surahs: Arabic name, ayah count, and the mushaf page range they span
// (standard 604-page Hafs 'an Asim layout — see pages.ts).

export interface SurahInfo {
	number: number;
	name: string;
	ayahCount: number;
	firstPage: number;
	lastPage: number;
}

export const SURAHS: readonly SurahInfo[] = [
	{
		number: 1,
		name: 'الفاتحة',
		ayahCount: 7,
		firstPage: 1,
		lastPage: 1
	},
	{
		number: 2,
		name: 'البقرة',
		ayahCount: 286,
		firstPage: 2,
		lastPage: 49
	},
	{
		number: 3,
		name: 'آل عمران',
		ayahCount: 200,
		firstPage: 50,
		lastPage: 76
	},
	{
		number: 4,
		name: 'النساء',
		ayahCount: 176,
		firstPage: 77,
		lastPage: 106
	},
	{
		number: 5,
		name: 'المائدة',
		ayahCount: 120,
		firstPage: 106,
		lastPage: 127
	},
	{
		number: 6,
		name: 'الأنعام',
		ayahCount: 165,
		firstPage: 128,
		lastPage: 150
	},
	{
		number: 7,
		name: 'الأعراف',
		ayahCount: 206,
		firstPage: 151,
		lastPage: 176
	},
	{
		number: 8,
		name: 'الأنفال',
		ayahCount: 75,
		firstPage: 177,
		lastPage: 186
	},
	{
		number: 9,
		name: 'التوبة',
		ayahCount: 129,
		firstPage: 187,
		lastPage: 207
	},
	{
		number: 10,
		name: 'يونس',
		ayahCount: 109,
		firstPage: 208,
		lastPage: 221
	},
	{
		number: 11,
		name: 'هود',
		ayahCount: 123,
		firstPage: 221,
		lastPage: 235
	},
	{
		number: 12,
		name: 'يوسف',
		ayahCount: 111,
		firstPage: 235,
		lastPage: 248
	},
	{
		number: 13,
		name: 'الرعد',
		ayahCount: 43,
		firstPage: 249,
		lastPage: 255
	},
	{
		number: 14,
		name: 'ابراهيم',
		ayahCount: 52,
		firstPage: 255,
		lastPage: 261
	},
	{
		number: 15,
		name: 'الحجر',
		ayahCount: 99,
		firstPage: 262,
		lastPage: 267
	},
	{
		number: 16,
		name: 'النحل',
		ayahCount: 128,
		firstPage: 267,
		lastPage: 281
	},
	{
		number: 17,
		name: 'الإسراء',
		ayahCount: 111,
		firstPage: 282,
		lastPage: 293
	},
	{
		number: 18,
		name: 'الكهف',
		ayahCount: 110,
		firstPage: 293,
		lastPage: 304
	},
	{
		number: 19,
		name: 'مريم',
		ayahCount: 98,
		firstPage: 305,
		lastPage: 312
	},
	{
		number: 20,
		name: 'طه',
		ayahCount: 135,
		firstPage: 312,
		lastPage: 321
	},
	{
		number: 21,
		name: 'الأنبياء',
		ayahCount: 112,
		firstPage: 322,
		lastPage: 331
	},
	{
		number: 22,
		name: 'الحج',
		ayahCount: 78,
		firstPage: 332,
		lastPage: 341
	},
	{
		number: 23,
		name: 'المؤمنون',
		ayahCount: 118,
		firstPage: 342,
		lastPage: 349
	},
	{
		number: 24,
		name: 'النور',
		ayahCount: 64,
		firstPage: 350,
		lastPage: 359
	},
	{
		number: 25,
		name: 'الفرقان',
		ayahCount: 77,
		firstPage: 359,
		lastPage: 366
	},
	{
		number: 26,
		name: 'الشعراء',
		ayahCount: 227,
		firstPage: 367,
		lastPage: 376
	},
	{
		number: 27,
		name: 'النمل',
		ayahCount: 93,
		firstPage: 377,
		lastPage: 385
	},
	{
		number: 28,
		name: 'القصص',
		ayahCount: 88,
		firstPage: 385,
		lastPage: 396
	},
	{
		number: 29,
		name: 'العنكبوت',
		ayahCount: 69,
		firstPage: 396,
		lastPage: 404
	},
	{
		number: 30,
		name: 'الروم',
		ayahCount: 60,
		firstPage: 404,
		lastPage: 410
	},
	{
		number: 31,
		name: 'لقمان',
		ayahCount: 34,
		firstPage: 411,
		lastPage: 414
	},
	{
		number: 32,
		name: 'السجدة',
		ayahCount: 30,
		firstPage: 415,
		lastPage: 417
	},
	{
		number: 33,
		name: 'الأحزاب',
		ayahCount: 73,
		firstPage: 418,
		lastPage: 427
	},
	{
		number: 34,
		name: 'سبإ',
		ayahCount: 54,
		firstPage: 428,
		lastPage: 434
	},
	{
		number: 35,
		name: 'فاطر',
		ayahCount: 45,
		firstPage: 434,
		lastPage: 440
	},
	{
		number: 36,
		name: 'يس',
		ayahCount: 83,
		firstPage: 440,
		lastPage: 445
	},
	{
		number: 37,
		name: 'الصافات',
		ayahCount: 182,
		firstPage: 446,
		lastPage: 452
	},
	{
		number: 38,
		name: 'ص',
		ayahCount: 88,
		firstPage: 453,
		lastPage: 458
	},
	{
		number: 39,
		name: 'الزمر',
		ayahCount: 75,
		firstPage: 458,
		lastPage: 467
	},
	{
		number: 40,
		name: 'غافر',
		ayahCount: 85,
		firstPage: 467,
		lastPage: 476
	},
	{
		number: 41,
		name: 'فصلت',
		ayahCount: 54,
		firstPage: 477,
		lastPage: 482
	},
	{
		number: 42,
		name: 'الشورى',
		ayahCount: 53,
		firstPage: 483,
		lastPage: 489
	},
	{
		number: 43,
		name: 'الزخرف',
		ayahCount: 89,
		firstPage: 489,
		lastPage: 495
	},
	{
		number: 44,
		name: 'الدخان',
		ayahCount: 59,
		firstPage: 496,
		lastPage: 498
	},
	{
		number: 45,
		name: 'الجاثية',
		ayahCount: 37,
		firstPage: 499,
		lastPage: 502
	},
	{
		number: 46,
		name: 'الأحقاف',
		ayahCount: 35,
		firstPage: 502,
		lastPage: 506
	},
	{
		number: 47,
		name: 'محمد',
		ayahCount: 38,
		firstPage: 507,
		lastPage: 510
	},
	{
		number: 48,
		name: 'الفتح',
		ayahCount: 29,
		firstPage: 511,
		lastPage: 515
	},
	{
		number: 49,
		name: 'الحجرات',
		ayahCount: 18,
		firstPage: 515,
		lastPage: 517
	},
	{
		number: 50,
		name: 'ق',
		ayahCount: 45,
		firstPage: 518,
		lastPage: 520
	},
	{
		number: 51,
		name: 'الذاريات',
		ayahCount: 60,
		firstPage: 520,
		lastPage: 523
	},
	{
		number: 52,
		name: 'الطور',
		ayahCount: 49,
		firstPage: 523,
		lastPage: 525
	},
	{
		number: 53,
		name: 'النجم',
		ayahCount: 62,
		firstPage: 526,
		lastPage: 528
	},
	{
		number: 54,
		name: 'القمر',
		ayahCount: 55,
		firstPage: 528,
		lastPage: 531
	},
	{
		number: 55,
		name: 'الرحمن',
		ayahCount: 78,
		firstPage: 531,
		lastPage: 534
	},
	{
		number: 56,
		name: 'الواقعة',
		ayahCount: 96,
		firstPage: 534,
		lastPage: 537
	},
	{
		number: 57,
		name: 'الحديد',
		ayahCount: 29,
		firstPage: 537,
		lastPage: 541
	},
	{
		number: 58,
		name: 'المجادلة',
		ayahCount: 22,
		firstPage: 542,
		lastPage: 545
	},
	{
		number: 59,
		name: 'الحشر',
		ayahCount: 24,
		firstPage: 545,
		lastPage: 548
	},
	{
		number: 60,
		name: 'الممتحنة',
		ayahCount: 13,
		firstPage: 549,
		lastPage: 551
	},
	{
		number: 61,
		name: 'الصف',
		ayahCount: 14,
		firstPage: 551,
		lastPage: 552
	},
	{
		number: 62,
		name: 'الجمعة',
		ayahCount: 11,
		firstPage: 553,
		lastPage: 554
	},
	{
		number: 63,
		name: 'المنافقون',
		ayahCount: 11,
		firstPage: 554,
		lastPage: 555
	},
	{
		number: 64,
		name: 'التغابن',
		ayahCount: 18,
		firstPage: 556,
		lastPage: 557
	},
	{
		number: 65,
		name: 'الطلاق',
		ayahCount: 12,
		firstPage: 558,
		lastPage: 559
	},
	{
		number: 66,
		name: 'التحريم',
		ayahCount: 12,
		firstPage: 560,
		lastPage: 561
	},
	{
		number: 67,
		name: 'الملك',
		ayahCount: 30,
		firstPage: 562,
		lastPage: 564
	},
	{
		number: 68,
		name: 'القلم',
		ayahCount: 52,
		firstPage: 564,
		lastPage: 566
	},
	{
		number: 69,
		name: 'الحاقة',
		ayahCount: 52,
		firstPage: 566,
		lastPage: 568
	},
	{
		number: 70,
		name: 'المعارج',
		ayahCount: 44,
		firstPage: 568,
		lastPage: 570
	},
	{
		number: 71,
		name: 'نوح',
		ayahCount: 28,
		firstPage: 570,
		lastPage: 571
	},
	{
		number: 72,
		name: 'الجن',
		ayahCount: 28,
		firstPage: 572,
		lastPage: 573
	},
	{
		number: 73,
		name: 'المزمل',
		ayahCount: 20,
		firstPage: 574,
		lastPage: 575
	},
	{
		number: 74,
		name: 'المدثر',
		ayahCount: 56,
		firstPage: 575,
		lastPage: 577
	},
	{
		number: 75,
		name: 'القيامة',
		ayahCount: 40,
		firstPage: 577,
		lastPage: 578
	},
	{
		number: 76,
		name: 'الانسان',
		ayahCount: 31,
		firstPage: 578,
		lastPage: 580
	},
	{
		number: 77,
		name: 'المرسلات',
		ayahCount: 50,
		firstPage: 580,
		lastPage: 581
	},
	{
		number: 78,
		name: 'النبإ',
		ayahCount: 40,
		firstPage: 582,
		lastPage: 583
	},
	{
		number: 79,
		name: 'النازعات',
		ayahCount: 46,
		firstPage: 583,
		lastPage: 584
	},
	{
		number: 80,
		name: 'عبس',
		ayahCount: 42,
		firstPage: 585,
		lastPage: 585
	},
	{
		number: 81,
		name: 'التكوير',
		ayahCount: 29,
		firstPage: 586,
		lastPage: 586
	},
	{
		number: 82,
		name: 'الإنفطار',
		ayahCount: 19,
		firstPage: 587,
		lastPage: 587
	},
	{
		number: 83,
		name: 'المطففين',
		ayahCount: 36,
		firstPage: 587,
		lastPage: 589
	},
	{
		number: 84,
		name: 'الإنشقاق',
		ayahCount: 25,
		firstPage: 589,
		lastPage: 589
	},
	{
		number: 85,
		name: 'البروج',
		ayahCount: 22,
		firstPage: 590,
		lastPage: 590
	},
	{
		number: 86,
		name: 'الطارق',
		ayahCount: 17,
		firstPage: 591,
		lastPage: 591
	},
	{
		number: 87,
		name: 'الأعلى',
		ayahCount: 19,
		firstPage: 591,
		lastPage: 592
	},
	{
		number: 88,
		name: 'الغاشية',
		ayahCount: 26,
		firstPage: 592,
		lastPage: 592
	},
	{
		number: 89,
		name: 'الفجر',
		ayahCount: 30,
		firstPage: 593,
		lastPage: 594
	},
	{
		number: 90,
		name: 'البلد',
		ayahCount: 20,
		firstPage: 594,
		lastPage: 594
	},
	{
		number: 91,
		name: 'الشمس',
		ayahCount: 15,
		firstPage: 595,
		lastPage: 595
	},
	{
		number: 92,
		name: 'الليل',
		ayahCount: 21,
		firstPage: 595,
		lastPage: 596
	},
	{
		number: 93,
		name: 'الضحى',
		ayahCount: 11,
		firstPage: 596,
		lastPage: 596
	},
	{
		number: 94,
		name: 'الشرح',
		ayahCount: 8,
		firstPage: 596,
		lastPage: 596
	},
	{
		number: 95,
		name: 'التين',
		ayahCount: 8,
		firstPage: 597,
		lastPage: 597
	},
	{
		number: 96,
		name: 'العلق',
		ayahCount: 19,
		firstPage: 597,
		lastPage: 597
	},
	{
		number: 97,
		name: 'القدر',
		ayahCount: 5,
		firstPage: 598,
		lastPage: 598
	},
	{
		number: 98,
		name: 'البينة',
		ayahCount: 8,
		firstPage: 598,
		lastPage: 599
	},
	{
		number: 99,
		name: 'الزلزلة',
		ayahCount: 8,
		firstPage: 599,
		lastPage: 599
	},
	{
		number: 100,
		name: 'العاديات',
		ayahCount: 11,
		firstPage: 599,
		lastPage: 600
	},
	{
		number: 101,
		name: 'القارعة',
		ayahCount: 11,
		firstPage: 600,
		lastPage: 600
	},
	{
		number: 102,
		name: 'التكاثر',
		ayahCount: 8,
		firstPage: 600,
		lastPage: 600
	},
	{
		number: 103,
		name: 'العصر',
		ayahCount: 3,
		firstPage: 601,
		lastPage: 601
	},
	{
		number: 104,
		name: 'الهمزة',
		ayahCount: 9,
		firstPage: 601,
		lastPage: 601
	},
	{
		number: 105,
		name: 'الفيل',
		ayahCount: 5,
		firstPage: 601,
		lastPage: 601
	},
	{
		number: 106,
		name: 'قريش',
		ayahCount: 4,
		firstPage: 602,
		lastPage: 602
	},
	{
		number: 107,
		name: 'الماعون',
		ayahCount: 7,
		firstPage: 602,
		lastPage: 602
	},
	{
		number: 108,
		name: 'الكوثر',
		ayahCount: 3,
		firstPage: 602,
		lastPage: 602
	},
	{
		number: 109,
		name: 'الكافرون',
		ayahCount: 6,
		firstPage: 603,
		lastPage: 603
	},
	{
		number: 110,
		name: 'النصر',
		ayahCount: 3,
		firstPage: 603,
		lastPage: 603
	},
	{
		number: 111,
		name: 'المسد',
		ayahCount: 5,
		firstPage: 603,
		lastPage: 603
	},
	{
		number: 112,
		name: 'الإخلاص',
		ayahCount: 4,
		firstPage: 604,
		lastPage: 604
	},
	{
		number: 113,
		name: 'الفلق',
		ayahCount: 5,
		firstPage: 604,
		lastPage: 604
	},
	{
		number: 114,
		name: 'الناس',
		ayahCount: 6,
		firstPage: 604,
		lastPage: 604
	}
];
