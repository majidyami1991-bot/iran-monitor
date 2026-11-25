export type Lang = 'fa' | 'en';

export interface Translations {
  // Brand
  brandName: string;
  brandTagline: string;
  loginBrandSubtitle: string;

  // Nav
  navOverview: string;
  navNews: string;
  navBriefing: string;
  navStories: string;
  navForesight: string;
  navForesightTrends: string;
  navForesightDrivers: string;
  navForesightUncertainties: string;
  navForesightWeakSignals: string;
  navForesightScenarios: string;
  navMonitoring: string;
  navMonitoringActivity: string;
  navMonitoringSources: string;
  navMonitoringTopics: string;
  navMonitoringCategories: string;
  navMonitoringAlerts: string;
  navMonitoringSocial: string;
  navAbout: string;
  navAdmin: string;

  // Shell & Chrome
  searchPlaceholder: string;
  searchNewsAria: string;
  liveStatus: string;
  syncingStatus: string;
  degradedStatus: string;
  openMenuAria: string;
  closeMenuAria: string;
  mainMenu: string;
  mobileNav: string;
  notificationsTitle: string;
  noNotifications: string;
  loginBtn: string;
  logoutBtn: string;
  footerPlatform: string;
  footerAbout: string;
  footerMonitoring: string;
  footerSources: string;
  footerAdmin: string;
  allRightsReserved: string;

  // Home Page
  leadNoNews: string;
  latestNewsTitle: string;
  latestNewsKicker: string;
  allNewsAction: string;
  sortLabel: string;
  sortNewest: string;
  sortImportant7d: string;
  sortCoverage7d: string;
  moreNewsAria: string;
  timelineTitle: string;
  timelineKicker: string;
  allEventsAction: string;
  timelineSortLabel: string;
  timelineSortLatest: string;
  timelineSortImportant: string;
  timelineEmpty: string;
  activityTitle: string;
  activityKicker: string;
  analyticsAction: string;
  activityPast48h: string;
  statPastHour: string;
  statPast24h: string;
  statVsYesterday: string;
  statPast7d: string;
  newsUnit: string;
  commodityPricesTitle: string;
  commodityPricesNote: string;

  // Daily Briefing
  dailyBriefingEyebrow: string;
  whatHappenedToday: string;
  ruleBasedNoAi: string;
  briefFresh: string;
  briefStale: string;
  briefOutdated: string;
  briefNotGenerated: string;
  articles24h: string;
  vsPrev24h: string;
  activeSourcesCount: string;
  keyDevelopments: string;
  noKeyDevelopments: string;
  risingTopics: string;
  fallingTopics: string;
  noRisingTopics: string;
  noFallingTopics: string;
  briefingEmptyTitle: string;
  briefingEmptyDesc: string;
  briefingFailed: string;

  // News Stream & Filters
  newsStreamEyebrow: string;
  newsStreamTitle: string;
  newsStreamLede: string;
  filtersTitle: string;
  filterSearchLabel: string;
  filterSearchPlaceholder: string;
  filterSourceLabel: string;
  filterAllSources: string;
  filterCategoryLabel: string;
  filterAllCategories: string;
  filterOtherCategory: string;
  filterSubtopicLabel: string;
  filterAllSubtopics: string;
  filterWindowLabel: string;
  filterAllTimes: string;
  filterWindow1h: string;
  filterWindow24h: string;
  filterWindow7d: string;
  filterWindow30d: string;
  filterLangLabel: string;
  filterAllLangs: string;
  filterLangEn: string;
  filterLangFa: string;
  filterImportanceLabel: string;
  filterImportanceAll: string;
  filterImportanceHigh: string;
  filterImportanceMed: string;
  filterImportanceLow: string;
  filterSortLabel: string;
  filterOldest: string;
  clearFilters: string;
  showingResults: string;

  // Common UI
  loadingText: string;
  retryBtn: string;
  emptyResults: string;
  prevPage: string;
  nextPage: string;
  pageOf: string;
  originalSourceText: string;
  sourceNotRecorded: string;
  timeNotRecorded: string;

  // UI Primitives & Tags
  tagUncategorized: string;
  importanceHigh: string;
  importanceMed: string;
  importanceLow: string;
  importanceTitle: string;
  tagBreaking: string;
  tagMachineLabel: string;
  tagAiGenerated: string;
  translationQcPassTitle: string;
  translationQcWarnLabel: string;
  translationQcWarnTitle: string;
  translationQcFailedLabel: string;
  translationQcFailedTitle: string;
  translationProcessingLabel: string;
  translationPendingLabel: string;
  translationPendingTitle: string;
  translationFailedLabel: string;
  translationFailedTitle: string;
  translationNoTextLabel: string;
  translationNoTextTitle: string;
  translationErrorLabel: string;
  translationErrorTitle: string;
  translationMachine: string;
  translationReviewed: string;
  translationPendingReview: string;
  translationUnreviewed: string;
  translationUnavailable: string;
  translationQcRejected: string;
  translationStale: string;
  translationNotRequired: string;
  failureDefault: string;
  retryAction: string;
  pagerAria: string;
  pagerPrev: string;
  pagerNext: string;
  pagerPage: string;
  pagerItems: string;
  statusActive: string;
  statusConfigured: string;
  statusStale: string;
  statusBlocked: string;
  statusNotConfigured: string;
  statusManualOnly: string;
  noMockDataNote: string;
  dataConnection: string;

  // News Card & Stream
  cardFaWarnTitle: string;
  cardFaQcFailed: string;
  cardFaTranslationError: string;
  cardFaPending: string;
  cardPublishedAt: string;
  cardPubNotRecorded: string;
  cardPubNotRecordedShort: string;
  cardSummaryMissingPublisher: string;
  cardSummaryMissingGeneric: string;
  cardEventArticles: string;
  cardEventPartPrefix: string;
  cardEventArticlesWord: string;
  cardEventSourcesWord: string;
  filterDateFrom: string;
  filterDateTo: string;
  filterTransAvailable: string;
  filterTransWarning: string;
  filterTransFailed: string;
  filterTransPending: string;
  filterTransError: string;
  filterLangUnknown: string;

  // News Detail
  navBreadcrumb: string;
  newsDetailNotFound: string;
  viewOnSource: string;
  publishedLabel: string;
  feedNotRecorded: string;
  bilingualTextHeading: string;
  persianColHeading: string;
  fieldTitleLabel: string;
  fieldSummaryLabel: string;
  fieldPublisherSummaryLabel: string;
  fieldArticleBodyLabel: string;
  fieldBodyTranslationLabel: string;
  noBodyTextPublished: string;
  englishColHeading: string;
  unspecifiedLanguage: string;
  noSourceTextPublished: string;
  aiNoticeLocalProvider: string;
  aiNoticeModel: string;
  aiNoticeQc: string;
  aiNoticeDisclaimer: string;
  keyPointsTitle: string;
  keyPointsAiTag: string;
  attachedDocsTitle: string;
  invalidUrl: string;
  unknownType: string;
  verified: string;
  unverified: string;
  noAutoDownload: string;
  sameEventTitle: string;
  eventPageLink: string;
  otherNewsInCategory: string;
  provenanceAndClassification: string;
  provenanceHeading: string;
  sourceProvenanceLabel: string;
  ingestionMethodLabel: string;
  ingestionRssDesc: string;
  ingestionHtmlDesc: string;
  publishedAtLabel: string;
  receivedAtLabel: string;
  notRecordedLegacy: string;
  provenanceStatusLabel: string;
  statusComplete: string;
  statusUnknown: string;
  executionRefPrefix: string;
  textProvenanceLabel: string;
  charsCount: string;
  thematicClassification: string;
  versionPrefix: string;
  notClassifiedYet: string;
  primaryCategory: string;
  otherReasonLabel: string;
  confidenceLabel: string;
  evidenceCountNote: string;
  secondaryTopics: string;
  subtopicsLabel: string;
  evidenceLabel: string;
  methodLabel: string;
  methodHumanLocked: string;
  methodRules: string;
  previousClassification: string;
  classificationHistory: string;
  importanceHeading: string;
  importanceScore: string;
  policyFullSyndicated: string;
  policySummaryOnly: string;
  policyLinkOnly: string;
  changeAssigned: string;
  changeReclassified: string;
  changeHumanOverride: string;
  unknownSize: string;
  unitMB: string;
  unitKB: string;
  requestTranslationBtn: string;
  requestTranslationSent: string;
  requestTranslationError: string;
  aiOffEnglishNotice: string;

  // Login Page
  loginHeading: string;
  loginSubheading: string;
  usernameLabel: string;
  usernamePlaceholder: string;
  passwordLabel: string;
  passwordPlaceholder: string;
  rememberMe: string;
  showPasswordAria: string;
  hidePasswordAria: string;
  signInBtn: string;
  authenticatingBtn: string;
  loginRequiredError: string;
  loginFailedError: string;
  dragToRotateHelp: string;

  // Relative Time & Sources
  justNow: string;
  minutesAgo: string;
  hoursAgo: string;
  daysAgo: string;
  sourceLabel: string;
  sourcesLabel: string;
  sourceActive: string;
  sourcesActive: string;
  independentSource: string;
  independentSources: string;
  reportLabel: string;
}

export const DICTIONARY: Record<Lang, Translations> = {
  fa: {
    brandName: 'Defense Monitor',
    brandTagline: 'اتاق خبر رصد منابع باز دفاعی و راهبردی',
    loginBrandSubtitle: 'مرکز پردازش اطلاعات و پایش دفاعی',

    navOverview: 'دیدبان',
    navNews: 'اخبار',
    navBriefing: 'خلاصه روزانه',
    navStories: 'استوری‌ها',
    navForesight: 'آینده‌پژوهی',
    navForesightTrends: 'روندها',
    navForesightDrivers: 'پیشران‌ها',
    navForesightUncertainties: 'عدم‌قطعیت‌ها',
    navForesightWeakSignals: 'سیگنال‌های ضعیف',
    navForesightScenarios: 'سناریوها',
    navMonitoring: 'پایش و سلامت',
    navMonitoringActivity: 'فعالیت سامانه',
    navMonitoringSources: 'منابع و خوراک‌ها',
    navMonitoringTopics: 'دسته‌بندی موضوعی',
    navMonitoringCategories: 'پوشش رده‌ها',
    navMonitoringAlerts: 'هشدارهای فنی',
    navMonitoringSocial: 'دیدبان شبکه‌های اجتماعی',
    navAbout: 'درباره سامانه',
    navAdmin: 'مدیریت',

    searchPlaceholder: 'جست‌وجو…',
    searchNewsAria: 'جست‌وجو در اخبار',
    liveStatus: 'پایش زنده فعال است',
    syncingStatus: 'در حال به‌روزرسانی…',
    degradedStatus: 'هشدار عملکرد سامانه',
    openMenuAria: 'باز کردن منو',
    closeMenuAria: 'بستن منو',
    mainMenu: 'منوی اصلی',
    mobileNav: 'ناوبری موبایل',
    notificationsTitle: 'اعلان‌های سیستمی',
    noNotifications: 'پیام یا هشدار خوانده‌نشده‌ای وجود ندارد.',
    loginBtn: 'ورود',
    logoutBtn: 'خروج از حساب',
    footerPlatform: 'سامانه پایش اطلاعات آشکار دفاعی و امنیتی ایران',
    footerAbout: 'درباره',
    footerMonitoring: 'پایش',
    footerSources: 'منابع',
    footerAdmin: 'مدیریت',
    allRightsReserved: 'تمامی حقوق متعلق به مرکز پردازش اطلاعات و پایش دفاعی است.',

    leadNoNews: 'خبری برای نمایش نیست',
    latestNewsTitle: 'تازه‌ترین خبرها',
    latestNewsKicker: 'از همه منابع فعال، مستقیم از پایگاه داده',
    allNewsAction: 'همه خبرها',
    sortLabel: 'مرتب‌سازی',
    sortNewest: 'جدیدترین',
    sortImportant7d: 'مهم‌ترین (۷ روز)',
    sortCoverage7d: 'پربازتاب‌ترین (۷ روز)',
    moreNewsAria: 'خبرهای بیشتر',
    timelineTitle: 'خط زمانی رویدادها',
    timelineKicker: 'خبرهای هم‌موضوع از منابع مختلف که به یک رویداد پیوند خورده‌اند',
    allEventsAction: 'همه رویدادها',
    timelineSortLabel: 'ترتیب رویدادها',
    timelineSortLatest: 'جدیدترین',
    timelineSortImportant: 'مهم‌ترین',
    timelineEmpty: 'هنوز رویدادی شناسایی نشده است',
    activityTitle: 'فعالیت و تحلیل داده',
    activityKicker: 'فعالیت واقعی گردآوری و پوشش اطلاعاتی منابع',
    analyticsAction: 'تحلیل آماری',
    activityPast48h: 'فعالیت ۴۸ ساعت گذشته',
    statPastHour: 'یک ساعت اخیر',
    statPast24h: '۲۴ ساعت اخیر',
    statVsYesterday: 'تغییر نسبت به دیروز',
    statPast7d: '۷ روز گذشته',
    newsUnit: 'خبر',
    commodityPricesTitle: 'قیمت کالاها و انرژی',
    commodityPricesNote: 'قیمت کالا فقط از منبع دارای مجوز',

    dailyBriefingEyebrow: 'خلاصه روزانه',
    whatHappenedToday: 'امروز چه اتفاقی افتاد؟',
    ruleBasedNoAi: 'قاعده‌محور، بدون هوش مصنوعی',
    briefFresh: 'به‌روز',
    briefStale: 'قدیمی‌تر از یک ساعت',
    briefOutdated: 'قدیمی‌تر از ۲۴ ساعت',
    briefNotGenerated: 'تولید نشده',
    articles24h: 'خبر در ۲۴ ساعت',
    vsPrev24h: 'نسبت به ۲۴ ساعت قبل',
    activeSourcesCount: 'منبع فعال',
    keyDevelopments: 'تحولات کلیدی',
    noKeyDevelopments: 'در ۲۴ ساعت گذشته خبر موضوعی ثبت نشده است.',
    risingTopics: 'موضوعات در حال رشد',
    fallingTopics: 'موضوعات نزولی',
    noRisingTopics: 'هیچ موضوعی نسبت به ۲۴ ساعت قبل افزایش نداشته است.',
    noFallingTopics: 'هیچ موضوعی کاهش نداشته است.',
    briefingEmptyTitle: 'خلاصه روزانه هنوز تولید نشده است',
    briefingEmptyDesc: 'نخستین خلاصه پس از اولین اجرای زمان‌بند ساخته می‌شود.',
    briefingFailed: 'خلاصه روزانه دریافت نشد.',

    newsStreamEyebrow: 'جریان خبر',
    newsStreamTitle: 'اخبار پایش‌شده',
    newsStreamLede: 'همه خبرهای گردآوری‌شده از منابع فعال و پایگاه‌های اطلاعاتی.',
    filtersTitle: 'فیلترها',
    filterSearchLabel: 'جست‌وجو',
    filterSearchPlaceholder: 'واژه در عنوان یا خلاصه…',
    filterSourceLabel: 'منبع',
    filterAllSources: 'همه منابع',
    filterCategoryLabel: 'موضوع',
    filterAllCategories: 'همه موضوعات',
    filterOtherCategory: 'سایر (با دلیل مشخص)',
    filterSubtopicLabel: 'زیرموضوع',
    filterAllSubtopics: 'همه زیرموضوع‌ها',
    filterWindowLabel: 'بازه زمانی',
    filterAllTimes: 'همه زمان‌ها',
    filterWindow1h: 'یک ساعت اخیر',
    filterWindow24h: '۲۴ ساعت اخیر',
    filterWindow7d: '۷ روز اخیر',
    filterWindow30d: '۳۰ روز اخیر',
    filterLangLabel: 'زبان منبع',
    filterAllLangs: 'همه زبان‌ها',
    filterLangEn: 'انگلیسی',
    filterLangFa: 'فارسی',
    filterImportanceLabel: 'سطح اهمیت',
    filterImportanceAll: 'همه سطوح',
    filterImportanceHigh: 'اهمیت زیاد',
    filterImportanceMed: 'اهمیت متوسط',
    filterImportanceLow: 'اهمیت کم',
    filterSortLabel: 'مرتب‌سازی',
    filterOldest: 'قدیمی‌ترین',
    clearFilters: 'پاک کردن فیلترها',
    showingResults: 'نمایش نتایج',

    loadingText: 'در حال دریافت داده…',
    retryBtn: 'تلاش مجدد',
    emptyResults: 'موردی یافت نشد.',
    prevPage: 'صفحه قبل',
    nextPage: 'صفحه بعد',
    pageOf: 'صفحه {current} از {total}',
    originalSourceText: 'متن اصلی منبع',
    sourceNotRecorded: 'منبع نامشخص',
    timeNotRecorded: 'زمان انتشار در خوراک منبع ثبت نشده',

    // UI Primitives & Tags
    tagUncategorized: 'دسته‌بندی‌نشده',
    importanceHigh: 'اهمیت زیاد',
    importanceMed: 'اهمیت متوسط',
    importanceLow: 'اهمیت کم',
    importanceTitle: 'بر اساس قاعده importance_v1 — صفحه «درباره» را ببینید',
    tagBreaking: 'فوری',
    tagMachineLabel: 'ترجمه خودکار ـ تأیید انسانی نشده',
    tagAiGenerated: 'تولیدشده با هوش مصنوعی',
    translationQcPassTitle: 'کنترل کیفیت خودکار اشکالی نیافت',
    translationQcWarnLabel: 'ترجمه با هشدار کیفیت',
    translationQcWarnTitle: 'برخی موارد قابل تأیید خودکار نبود',
    translationQcFailedLabel: 'ترجمه رد شد (خطای کیفیت)',
    translationQcFailedTitle: 'کنترل کیفیت خطای بحرانی یافت؛ ترجمه نمایش داده نمی‌شود',
    translationProcessingLabel: 'در حال ترجمه',
    translationPendingLabel: 'در انتظار ترجمه',
    translationPendingTitle: 'در صف ترجمه خودکار؛ تا آماده شدن، متن اصلی نمایش داده می‌شود',
    translationFailedLabel: 'ترجمه ناموفق (دائمی)',
    translationFailedTitle: 'پس از چند تلاش ناموفق ماند',
    translationNoTextLabel: 'بدون متن برای ترجمه',
    translationNoTextTitle: 'منبع متنی برای ترجمه منتشر نکرده است',
    translationErrorLabel: 'خطای ترجمه',
    translationErrorTitle: 'ترجمه خودکار ناموفق بود و با تأخیر دوباره تلاش می‌شود',
    translationMachine: 'ترجمه ماشینی',
    translationReviewed: 'بازبینی‌شده',
    translationPendingReview: 'در صف بازبینی',
    translationUnreviewed: 'بازبینی‌نشده',
    translationUnavailable: 'ترجمه ناموجود',
    translationQcRejected: 'ترجمه ردشده در کنترل کیفیت',
    translationStale: 'متن اصلی تغییر کرده؛ ترجمه کهنه',
    translationNotRequired: 'متن اصلی فارسی است',
    failureDefault: 'دریافت داده از سرور ناموفق بود.',
    retryAction: 'تلاش دوباره',
    pagerAria: 'صفحه‌بندی',
    pagerPrev: 'صفحه قبل',
    pagerNext: 'صفحه بعد',
    pagerPage: 'صفحه',
    pagerItems: 'مورد',
    statusActive: 'فعال',
    statusConfigured: 'پیکربندی‌شده',
    statusStale: 'متوقف یا با تأخیر',
    statusBlocked: 'مسدود',
    statusNotConfigured: 'اتصال پیکربندی نشده',
    statusManualOnly: 'پایش دستی',
    noMockDataNote: '',
    dataConnection: 'اتصال داده',

    // News Card & Stream
    cardFaWarnTitle: 'ترجمه با هشدار کیفیت',
    cardFaQcFailed: 'ترجمه در کنترل کیفیت رد شد.',
    cardFaTranslationError: 'ترجمه ناموفق بود؛ دوباره تلاش می‌شود.',
    cardFaPending: 'در انتظار ترجمه خودکار…',
    cardPublishedAt: 'انتشار: ',
    cardPubNotRecorded: 'زمان انتشار در خوراک منبع ثبت نشده',
    cardPubNotRecordedShort: 'زمان انتشار ثبت نشده',
    cardSummaryMissingPublisher: 'منبع برای این خبر خلاصه‌ای منتشر نکرده است.',
    cardSummaryMissingGeneric: 'خلاصه‌ای برای این خبر ثبت نشده است.',
    cardEventArticles: 'خبر در رویداد',
    cardEventPartPrefix: 'بخشی از رویدادی با',
    cardEventArticlesWord: 'خبر از',
    cardEventSourcesWord: 'منبع',
    filterDateFrom: 'از {val}',
    filterDateTo: 'تا {val}',
    filterTransAvailable: 'ترجمه خودکار بدون ایراد کیفیت',
    filterTransWarning: 'ترجمه با هشدار کیفیت',
    filterTransFailed: 'ترجمه ردشده در کنترل کیفیت',
    filterTransPending: 'ترجمه در انتظار',
    filterTransError: 'خطای ترجمه',
    filterLangUnknown: 'زبان نامشخص',

    // News Detail
    navBreadcrumb: 'مسیر',
    newsDetailNotFound: 'این خبر پیدا نشد یا دریافت آن ناموفق بود.',
    viewOnSource: 'خبر در سایت منبع',
    publishedLabel: 'انتشار: ',
    feedNotRecorded: 'در خوراک ثبت نشده',
    bilingualTextHeading: 'متن دوزبانه',
    persianColHeading: 'فارسی',
    fieldTitleLabel: 'عنوان',
    fieldSummaryLabel: 'خلاصه',
    fieldPublisherSummaryLabel: 'خلاصه ناشر (RSS)',
    fieldArticleBodyLabel: 'متن کامل مقاله',
    fieldBodyTranslationLabel: 'ترجمه متن کامل',
    noBodyTextPublished: 'متن کاملی برای این مقاله استخراج نشده است.',
    englishColHeading: 'متن اصلی منبع (انگلیسی)',
    unspecifiedLanguage: 'زبان اعلام‌نشده',
    noSourceTextPublished: 'ناشر برای این خبر متنی منتشر نکرده است.',
    aiNoticeLocalProvider: 'ترجمه محلی',
    aiNoticeModel: 'مدل',
    aiNoticeQc: 'کنترل کیفیت',
    aiNoticeDisclaimer: '',
    keyPointsTitle: 'نکات کلیدی',
    keyPointsAiTag: 'تولیدشده با هوش مصنوعی · نیازمند بازبینی',
    attachedDocsTitle: 'اسناد پیوست خبر',
    invalidUrl: 'نشانی نامعتبر',
    unknownType: 'نوع نامشخص',
    verified: 'بررسی‌شده',
    unverified: 'بررسی‌نشده',
    noAutoDownload: 'دانلود خودکار نمی‌شود',
    sameEventTitle: 'همین رویداد در منابع دیگر',
    eventPageLink: 'صفحه رویداد',
    otherNewsInCategory: 'خبرهای دیگر در',
    provenanceAndClassification: 'منشأ و طبقه‌بندی',
    provenanceHeading: 'منشأ و مسیر دریافت',
    sourceProvenanceLabel: 'منبع',
    ingestionMethodLabel: 'روش گردآوری',
    ingestionRssDesc: 'خوراک RSS ناشر، یک درخواست در هر چرخه',
    ingestionHtmlDesc: 'استخراج مستقیم HTML، با مدیریت بارگذاری',
    publishedAtLabel: 'زمان انتشار',
    receivedAtLabel: 'زمان دریافت',
    notRecordedLegacy: 'ثبت نشده (رکورد پیش از ثبت زمان دریافت)',
    provenanceStatusLabel: 'وضعیت منشأ',
    statusComplete: 'کامل',
    statusUnknown: 'نامشخص',
    executionRefPrefix: 'اجرای',
    textProvenanceLabel: 'متن',
    charsCount: 'نویسه',
    thematicClassification: 'طبقه‌بندی موضوعی',
    versionPrefix: 'نسخه',
    notClassifiedYet: 'هنوز طبقه‌بندی نشده',
    primaryCategory: 'دسته اصلی',
    otherReasonLabel: 'دلیل «سایر»',
    confidenceLabel: 'اطمینان',
    evidenceCountNote: '(شمارش شواهد، نه احتمال)',
    secondaryTopics: 'موضوعات فرعی',
    subtopicsLabel: 'زیرموضوع‌ها',
    evidenceLabel: 'شواهد',
    methodLabel: 'روش',
    methodHumanLocked: 'اصلاح انسانی (قفل‌شده)',
    methodRules: 'قواعد کلیدواژه‌ای قطعی',
    previousClassification: 'طبقه‌بندی قبلی',
    classificationHistory: 'تاریخچه طبقه‌بندی',
    importanceHeading: 'اهمیت',
    importanceScore: 'امتیاز',
    policyFullSyndicated: 'متن کامل در خوراک خود ناشر منتشر شده است.',
    policySummaryOnly: 'ناشر فقط خلاصه را در خوراک منتشر کرده است؛ متن کامل بازنشر نمی‌شود.',
    policyLinkOnly: 'ناشر متن را در خوراک منتشر نکرده است؛ فقط پیوند به منبع نمایش داده می‌شود.',
    changeAssigned: 'تخصیص اولیه',
    changeReclassified: 'بازطبقه‌بندی',
    changeHumanOverride: 'اصلاح انسانی',
    unknownSize: 'حجم نامشخص',
    unitMB: 'مگابایت',
    unitKB: 'کیلوبایت',
    requestTranslationBtn: 'اولویت دادن به ترجمه این خبر',
    requestTranslationSent: 'در صف ترجمه قرار گرفت؛ پس از آماده شدن، بدون نیاز به بارگذاری دوباره نمایش داده می‌شود.',
    requestTranslationError: 'ثبت درخواست ناموفق بود؛ دوباره تلاش کنید',
    aiOffEnglishNotice: '',

    loginHeading: 'Defense Monitor',
    loginSubheading: 'مرکز پردازش اطلاعات و پایش دفاعی',
    usernameLabel: 'نام کاربری',
    usernamePlaceholder: 'نام کاربری سازمانی (مانند admin یا r.karimi)',
    passwordLabel: 'رمز عبور',
    passwordPlaceholder: 'کلمه عبور امنیتی…',
    rememberMe: 'مرا به خاطر بسپار',
    showPasswordAria: 'نمایش رمز عبور',
    hidePasswordAria: 'مخفی کردن رمز عبور',
    signInBtn: 'ورود به سامانه',
    authenticatingBtn: 'در حال احراز هویت…',
    loginRequiredError: 'لطفاً نام کاربری و رمز عبور را وارد فرمایید.',
    loginFailedError: 'ورود ناموفق بود. نام کاربری یا کلمه عبور صحیح نمی‌باشد.',
    dragToRotateHelp: 'چرخش کره با کشیدن ماوس (افقی)',

    justNow: 'همین الان',
    minutesAgo: '{val} دقیقه پیش',
    hoursAgo: '{val} ساعت پیش',
    daysAgo: '{val} روز پیش',
    sourceLabel: 'منبع',
    sourcesLabel: 'منابع',
    sourceActive: 'منبع فعال',
    sourcesActive: 'منابع فعال',
    independentSource: 'منبع مستقل',
    independentSources: 'منبع مستقل',
    reportLabel: 'گزارش'
  },

  en: {
    brandName: 'Defense Monitor',
    brandTagline: 'Open Source Defense & Strategic Intelligence Newsroom',
    loginBrandSubtitle: 'Information Processing & Defense Monitoring Center',

    navOverview: 'Overview',
    navNews: 'News Feed',
    navBriefing: 'Daily Briefing',
    navStories: 'Stories',
    navForesight: 'Foresight',
    navForesightTrends: 'Trends',
    navForesightDrivers: 'Drivers',
    navForesightUncertainties: 'Uncertainties',
    navForesightWeakSignals: 'Weak Signals',
    navForesightScenarios: 'Scenarios',
    navMonitoring: 'Monitoring & Health',
    navMonitoringActivity: 'System Activity',
    navMonitoringSources: 'Sources & Feeds',
    navMonitoringTopics: 'Taxonomy & Topics',
    navMonitoringCategories: 'Categories',
    navMonitoringAlerts: 'Technical Alerts',
    navMonitoringSocial: 'Social Monitor',
    navAbout: 'About',
    navAdmin: 'Admin',

    searchPlaceholder: 'Search news…',
    searchNewsAria: 'Search news stream',
    liveStatus: 'Live monitoring active',
    syncingStatus: 'Synchronizing feeds…',
    degradedStatus: 'System alert',
    openMenuAria: 'Open menu',
    closeMenuAria: 'Close menu',
    mainMenu: 'Main Menu',
    mobileNav: 'Mobile Navigation',
    notificationsTitle: 'System Notifications',
    noNotifications: 'No unread notifications or alerts.',
    loginBtn: 'Sign In',
    logoutBtn: 'Sign Out',
    footerPlatform: 'Iran Defense & Security Open Source Intelligence Platform',
    footerAbout: 'About',
    footerMonitoring: 'Monitoring',
    footerSources: 'Sources',
    footerAdmin: 'Admin',
    allRightsReserved: 'All rights reserved by Information Processing & Defense Monitoring Center.',

    leadNoNews: 'No articles to display',
    latestNewsTitle: 'Latest Intelligence',
    latestNewsKicker: 'From all active monitored feeds, direct from database',
    allNewsAction: 'All News',
    sortLabel: 'Sort by',
    sortNewest: 'Newest',
    sortImportant7d: 'Most Important (7d)',
    sortCoverage7d: 'Top Coverage (7d)',
    moreNewsAria: 'More articles',
    timelineTitle: 'Events Timeline',
    timelineKicker: 'Multi-source correlated articles grouped into evolving events',
    allEventsAction: 'All Events',
    timelineSortLabel: 'Order by',
    timelineSortLatest: 'Latest',
    timelineSortImportant: 'Important',
    timelineEmpty: 'No correlated events detected yet',
    activityTitle: 'Activity & Data Analytics',
    activityKicker: 'Live ingestion volume, source coverage, and throughput telemetry',
    analyticsAction: 'Analytics',
    activityPast48h: 'Activity (Past 48 Hours)',
    statPastHour: 'Past Hour',
    statPast24h: 'Past 24 Hours',
    statVsYesterday: 'Change vs Yesterday',
    statPast7d: 'Past 7 Days',
    newsUnit: 'articles',
    commodityPricesTitle: 'Commodity & Energy Prices',
    commodityPricesNote: 'Licensed authorized market feeds only',

    dailyBriefingEyebrow: 'Daily Briefing',
    whatHappenedToday: 'What Happened Today?',
    ruleBasedNoAi: 'Rule-Based Deterministic Assessment',
    briefFresh: 'Up to date',
    briefStale: 'Older than 1 hour',
    briefOutdated: 'Older than 24 hours',
    briefNotGenerated: 'Not generated',
    articles24h: 'articles in 24h',
    vsPrev24h: 'vs previous 24h',
    activeSourcesCount: 'active sources',
    keyDevelopments: 'Key Developments',
    noKeyDevelopments: 'No key developments identified in the past 24 hours.',
    risingTopics: 'Rising Topics',
    fallingTopics: 'Decreasing Topics',
    noRisingTopics: 'No topic volume increases detected vs prior 24h.',
    noFallingTopics: 'No topic volume decreases detected.',
    briefingEmptyTitle: 'Daily Briefing Not Generated Yet',
    briefingEmptyDesc: 'Generated automatically following the 15-minute ingestion schedule.',
    briefingFailed: 'Failed to retrieve daily briefing.',

    newsStreamEyebrow: 'News Feed',
    newsStreamTitle: 'Monitored News Stream',
    newsStreamLede: 'All ingested articles across verified geopolitical and defense sources.',
    filtersTitle: 'Filters',
    filterSearchLabel: 'Search',
    filterSearchPlaceholder: 'Keywords in headline or summary…',
    filterSourceLabel: 'Source',
    filterAllSources: 'All Sources',
    filterCategoryLabel: 'Category',
    filterAllCategories: 'All Categories',
    filterOtherCategory: 'Other / Unclassified',
    filterSubtopicLabel: 'Subtopic',
    filterAllSubtopics: 'All Subtopics',
    filterWindowLabel: 'Time Window',
    filterAllTimes: 'All Time',
    filterWindow1h: 'Past Hour',
    filterWindow24h: 'Past 24 Hours',
    filterWindow7d: 'Past 7 Days',
    filterWindow30d: 'Past 30 Days',
    filterLangLabel: 'Source Language',
    filterAllLangs: 'All Languages',
    filterLangEn: 'English',
    filterLangFa: 'Persian',
    filterImportanceLabel: 'Importance Level',
    filterImportanceAll: 'All Levels',
    filterImportanceHigh: 'High Importance',
    filterImportanceMed: 'Medium Importance',
    filterImportanceLow: 'Low Importance',
    filterSortLabel: 'Sort Order',
    filterOldest: 'Oldest',
    clearFilters: 'Clear Filters',
    showingResults: 'Showing Results',

    loadingText: 'Loading intelligence data…',
    retryBtn: 'Retry',
    emptyResults: 'No records found matching criteria.',
    prevPage: 'Previous Page',
    nextPage: 'Next Page',
    pageOf: 'Page {current} of {total}',
    originalSourceText: 'Original publisher text',
    sourceNotRecorded: 'Unknown Source',
    timeNotRecorded: 'Publication timestamp not provided in source feed',

    // UI Primitives & Tags
    tagUncategorized: 'Uncategorized',
    importanceHigh: 'High Importance',
    importanceMed: 'Medium Importance',
    importanceLow: 'Low Importance',
    importanceTitle: 'Based on importance_v1 rule — see About page',
    tagBreaking: 'Breaking',
    tagMachineLabel: 'Machine translation — not human-verified',
    tagAiGenerated: 'AI Generated',
    translationQcPassTitle: 'Automated QC passed',
    translationQcWarnLabel: 'Translation with QC warning',
    translationQcWarnTitle: 'Quality check warning',
    translationQcFailedLabel: 'Translation rejected (QC error)',
    translationQcFailedTitle: 'Critical QC error found; translation suppressed',
    translationProcessingLabel: 'Translating…',
    translationPendingLabel: 'Pending translation',
    translationPendingTitle: 'Queued for machine translation; original text displayed meanwhile',
    translationFailedLabel: 'Translation failed',
    translationFailedTitle: 'Failed after multiple attempts',
    translationNoTextLabel: 'No text to translate',
    translationNoTextTitle: 'Publisher did not provide text for translation',
    translationErrorLabel: 'Translation error',
    translationErrorTitle: 'Automated translation failed; will retry with backoff',
    translationMachine: 'Machine translated',
    translationReviewed: 'Reviewed',
    translationPendingReview: 'Pending review',
    translationUnreviewed: 'Unreviewed',
    translationUnavailable: 'Translation unavailable',
    translationQcRejected: 'Rejected by QC',
    translationStale: 'Original text changed; stale translation',
    translationNotRequired: 'Original text is Persian',
    failureDefault: 'Failed to retrieve data from server.',
    retryAction: 'Retry',
    pagerAria: 'Pagination',
    pagerPrev: 'Previous Page',
    pagerNext: 'Next Page',
    pagerPage: 'Page',
    pagerItems: 'items',
    statusActive: 'Active',
    statusConfigured: 'Configured',
    statusStale: 'Stale / Delayed',
    statusBlocked: 'Blocked',
    statusNotConfigured: 'Not configured',
    statusManualOnly: 'Manual monitoring',
    noMockDataNote: '',
    dataConnection: 'Data Connection',

    // News Card & Stream
    cardFaWarnTitle: 'Translation quality warning',
    cardFaQcFailed: 'Translation rejected in QC.',
    cardFaTranslationError: 'Translation failed; will retry.',
    cardFaPending: 'Awaiting automated translation…',
    cardPublishedAt: 'Published: ',
    cardPubNotRecorded: 'Publication timestamp not recorded in source feed',
    cardPubNotRecordedShort: 'Publication time not recorded',
    cardSummaryMissingPublisher: 'Publisher did not provide a summary for this article.',
    cardSummaryMissingGeneric: 'No summary recorded for this article.',
    cardEventArticles: 'articles in event',
    cardEventPartPrefix: 'Part of event with',
    cardEventArticlesWord: 'articles from',
    cardEventSourcesWord: 'sources',
    filterDateFrom: 'From {val}',
    filterDateTo: 'To {val}',
    filterTransAvailable: 'Machine translation (QC Passed)',
    filterTransWarning: 'Translation with QC warning',
    filterTransFailed: 'Translation rejected by QC',
    filterTransPending: 'Translation pending',
    filterTransError: 'Translation error',
    filterLangUnknown: 'Unknown language',

    // News Detail
    navBreadcrumb: 'Breadcrumbs',
    newsDetailNotFound: 'Article not found or failed to load.',
    viewOnSource: 'View original source',
    publishedLabel: 'Published: ',
    feedNotRecorded: 'Not recorded in feed',
    bilingualTextHeading: 'Bilingual Text',
    persianColHeading: 'Persian',
    fieldTitleLabel: 'Title',
    fieldSummaryLabel: 'Summary',
    fieldPublisherSummaryLabel: 'Publisher Summary (RSS)',
    fieldArticleBodyLabel: 'Full Article Body',
    fieldBodyTranslationLabel: 'Full Body Translation',
    noBodyTextPublished: 'No full article text has been extracted for this item.',
    englishColHeading: 'Original Publisher Text (English)',
    unspecifiedLanguage: 'Unspecified language',
    noSourceTextPublished: 'Publisher did not release text for this item.',
    aiNoticeLocalProvider: 'Local translation',
    aiNoticeModel: 'Model',
    aiNoticeQc: 'QC',
    aiNoticeDisclaimer: '',
    keyPointsTitle: 'Key Developments',
    keyPointsAiTag: 'AI Generated · Review Required',
    attachedDocsTitle: 'Attached Documents',
    invalidUrl: 'Invalid URL',
    unknownType: 'Unknown type',
    verified: 'Verified',
    unverified: 'Unverified',
    noAutoDownload: 'Not automatically downloaded',
    sameEventTitle: 'Same Event in Other Sources',
    eventPageLink: 'Event Page',
    otherNewsInCategory: 'Other news in',
    provenanceAndClassification: 'Provenance & Classification',
    provenanceHeading: 'Provenance & Ingestion Route',
    sourceProvenanceLabel: 'Source',
    ingestionMethodLabel: 'Ingestion Method',
    ingestionRssDesc: 'Publisher RSS feed, one request per cycle',
    ingestionHtmlDesc: 'Direct HTML extraction with rate limiting',
    publishedAtLabel: 'Publication Time',
    receivedAtLabel: 'Ingestion Time',
    notRecordedLegacy: 'Not recorded (precedes timestamp tracking)',
    provenanceStatusLabel: 'Provenance Status',
    statusComplete: 'Complete',
    statusUnknown: 'Unknown',
    executionRefPrefix: 'Execution',
    textProvenanceLabel: 'Text',
    charsCount: 'chars',
    thematicClassification: 'Thematic Classification',
    versionPrefix: 'Version',
    notClassifiedYet: 'Not classified yet',
    primaryCategory: 'Primary Category',
    otherReasonLabel: 'Reason for "Other"',
    confidenceLabel: 'Confidence',
    evidenceCountNote: '(evidence count, not probability)',
    secondaryTopics: 'Secondary Topics',
    subtopicsLabel: 'Subtopics',
    evidenceLabel: 'Evidence',
    methodLabel: 'Method',
    methodHumanLocked: 'Human override (locked)',
    methodRules: 'Deterministic keyword rules',
    previousClassification: 'Previous Classification',
    classificationHistory: 'Classification History',
    importanceHeading: 'Importance',
    importanceScore: 'Score',
    policyFullSyndicated: 'Full text published directly in source feed.',
    policySummaryOnly: 'Publisher provided summary only; full article text not syndicated.',
    policyLinkOnly: 'Publisher provides link only; external reference retained.',
    changeAssigned: 'Initial assignment',
    changeReclassified: 'Reclassified',
    changeHumanOverride: 'Human override',
    unknownSize: 'Unknown size',
    unitMB: 'MB',
    unitKB: 'KB',
    requestTranslationBtn: 'Prioritize translation for this item',
    requestTranslationSent: 'Queued for translation; will appear automatically once processed.',
    requestTranslationError: 'Request failed; please retry.',
    aiOffEnglishNotice: '',

    loginHeading: 'Defense Monitor',
    loginSubheading: 'Information Processing & Defense Monitoring Center',
    usernameLabel: 'Username',
    usernamePlaceholder: 'Institutional username (e.g. admin or r.karimi)',
    passwordLabel: 'Password',
    passwordPlaceholder: 'Security credentials…',
    rememberMe: 'Remember this terminal',
    showPasswordAria: 'Show password',
    hidePasswordAria: 'Hide password',
    signInBtn: 'Sign In to Terminal',
    authenticatingBtn: 'Authenticating credentials…',
    loginRequiredError: 'Please enter both username and password.',
    loginFailedError: 'Authentication failed. Please verify your username and password.',
    dragToRotateHelp: 'Drag to spin globe horizontally',

    justNow: 'just now',
    minutesAgo: '{val}m ago',
    hoursAgo: '{val}h ago',
    daysAgo: '{val}d ago',
    sourceLabel: 'Source',
    sourcesLabel: 'Sources',
    sourceActive: 'active source',
    sourcesActive: 'active sources',
    independentSource: 'independent source',
    independentSources: 'independent sources',
    reportLabel: 'Report'
  }
};

export function getT(lang: Lang): Translations {
  return DICTIONARY[lang] || DICTIONARY.fa;
}

export { usePrefs } from './prefs';
