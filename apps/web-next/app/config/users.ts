export interface UserProfile {
  id: string;
  username: string;
  password: string;
  name: string;
  role: string;
  department: string;
  clearanceLevel: string;
  avatar: string;
  badgeColor: string;
}

export const PRESET_USERS: UserProfile[] = [
  {
    id: 'user_01',
    username: 'admin',
    password: 'IranMonitor@2026',
    name: 'مهندس علیرضا سلیمانی',
    role: 'مدیر ارشد سامانه',
    department: 'مرکز مدیریت و زیرساخت فرماندهی',
    clearanceLevel: 'سطح ۱ - فوق‌محرمانه',
    avatar: 'ع‌س',
    badgeColor: '#e3b341', // Gold / Amber
  },
  {
    id: 'user_02',
    username: 'dr_hosseini',
    password: 'Intel#2026',
    name: 'دکتر علی حسینی',
    role: 'تحلیل‌گر ارشد راهبردی',
    department: 'اتاق رصد و برآورد راهبردی',
    clearanceLevel: 'سطح ۱ - فوق‌محرمانه',
    avatar: 'ع‌ح',
    badgeColor: '#e3b341',
  },
  {
    id: 'user_03',
    username: 'm_rezaei',
    password: 'Defense@1405',
    name: 'سرگرد محمد رضایی',
    role: 'ناظر ارشد رصد اخبار دفاعی',
    department: 'قرارگاه پایش تهدیدات نظامی',
    clearanceLevel: 'سطح ۲ - خیلی محرمانه',
    avatar: 'م‌ر',
    badgeColor: '#ef5a4f', // Red / Defense
  },
  {
    id: 'user_04',
    username: 's_karimi',
    password: 'Osint#Lead1',
    name: 'مهندس سارا کریمی',
    role: 'سرپرست داده‌کاوی و OSINT',
    department: 'واحد جمع‌آوری منابع آشکار',
    clearanceLevel: 'سطح ۲ - خیلی محرمانه',
    avatar: 'س‌ک',
    badgeColor: '#4ea1ff', // Cyan / Intelligence
  },
  {
    id: 'user_05',
    username: 'cyber_lead',
    password: 'CyberShield!26',
    name: 'دکتر پوریا نجفی',
    role: 'متخصص ارشد امنیت و سایبر',
    department: 'مرکز رصد سایبری و جنگال',
    clearanceLevel: 'سطح ۱ - فوق‌محرمانه',
    avatar: 'پ‌ن',
    badgeColor: '#a78bfa', // Purple / Cyber
  },
  {
    id: 'user_06',
    username: 'f_moradi',
    password: 'Regional!99',
    name: 'فاطمه مرادی',
    role: 'کارشناس ژئوپلیتیک و خاورمیانه',
    department: 'اندیشکده مطالعات منطقه‌ای',
    clearanceLevel: 'سطح ۳ - محرمانه',
    avatar: 'ف‌م',
    badgeColor: '#3fbf7f', // Green
  },
  {
    id: 'user_07',
    username: 'ai_supervisor',
    password: 'TranslateGemma#1',
    name: 'مهندس مهدی کاظمی',
    role: 'ناظر مدل‌های هوش مصنوعی و ترجمه',
    department: 'آزمایشگاه مدل‌های زبانی بومی',
    clearanceLevel: 'سطح ۲ - خیلی محرمانه',
    avatar: 'م‌ک',
    badgeColor: '#a78bfa',
  },
  {
    id: 'user_08',
    username: 'editor_chief',
    password: 'DeskChief#2026',
    name: 'حمیدرضا باقری',
    role: 'سردبیر ارشد اتاق خبر',
    department: 'تحریریه و اعتبارسنجی منابع',
    clearanceLevel: 'سطح ۳ - محرمانه',
    avatar: 'ح‌ب',
    badgeColor: '#e8a13a',
  },
  {
    id: 'user_09',
    username: 'n_ebrahimi',
    password: 'Foresight#405',
    name: 'دکتر نیما ابراهیمی',
    role: 'پژوهشگر آینده‌پژوهی و سناریونویسی',
    department: 'میز آینده‌پژوهی دفاعی',
    clearanceLevel: 'سطح ۳ - محرمانه',
    avatar: 'ن‌ا',
    badgeColor: '#4ea1ff',
  },
  {
    id: 'user_10',
    username: 'guest_auditor',
    password: 'Auditor@Guest',
    name: 'کارشناس ناظر ارزیابی',
    role: 'ارزیاب دوره‌ای و ناظر کیفیت داده',
    department: 'بازرسی و اعتبارسنجی سیستم‌ها',
    clearanceLevel: 'سطح ۴ - عمومی سازمانی',
    avatar: 'ک‌ن',
    badgeColor: '#9aa7b4',
  },
];
