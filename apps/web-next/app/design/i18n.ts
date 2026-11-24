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
    dragToRotateHelp: 'چرخش کره با کشیدن ماوس (افقی)'
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
    dragToRotateHelp: 'Drag to spin globe horizontally'
  }
};

export function getT(lang: Lang): Translations {
  return DICTIONARY[lang] || DICTIONARY.fa;
}
