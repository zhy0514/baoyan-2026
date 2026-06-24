// utils.js — 工具函数

function formatDate(isoStr) {
  if (!isoStr) return '';
  const d = new Date(isoStr);
  return `${d.getMonth() + 1}月${d.getDate()}日`;
}

function formatDateTime(isoStr) {
  if (!isoStr) return '';
  const d = new Date(isoStr);
  const hm = `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
  return `${d.getMonth() + 1}月${d.getDate()}日 ${hm}`;
}

function daysLeft(isoStr) {
  if (!isoStr) return Infinity;
  const now = new Date();
  const deadline = new Date(isoStr);
  return Math.ceil((deadline - now) / (1000 * 60 * 60 * 24));
}

function relativeTime(isoStr) {
  const now = new Date();
  const then = new Date(isoStr);
  const diffMs = now - then;
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return '刚刚';
  if (diffMin < 60) return `${diffMin} 分钟前`;
  const diffHour = Math.floor(diffMin / 60);
  if (diffHour < 24) return `${diffHour} 小时前`;
  const diffDay = Math.floor(diffHour / 24);
  if (diffDay < 7) return `${diffDay} 天前`;
  return formatDate(isoStr);
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

// 所有985高校列表
const ALL_UNIVERSITIES = [
  '北京大学', '清华大学', '复旦大学', '上海交通大学', '浙江大学',
  '南京大学', '中国科学技术大学', '哈尔滨工业大学', '西安交通大学',
  '武汉大学', '华中科技大学', '同济大学', '北京航空航天大学', '北京理工大学',
  '中国人民大学', '北京师范大学', '南开大学', '天津大学', '大连理工大学',
  '东北大学', '吉林大学', '山东大学', '中国海洋大学', '厦门大学',
  '东南大学', '华东师范大学', '中山大学', '华南理工大学', '四川大学',
  '电子科技大学', '重庆大学', '湖南大学', '中南大学', '西北工业大学',
  '西北农林科技大学', '兰州大学', '国防科技大学', '中央民族大学', '中国农业大学'
];

const STATUS_MAP = {
  '报名中': 'active',
  '即将截止': 'soon',
  '已截止': 'closed',
  '待发布': 'pending'
};

const STATUS_TEXT = ['报名中', '即将截止', '已截止', '待发布'];
