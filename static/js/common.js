/* Shared API, theme, language and navigation. Never set innerHTML from server responses. */
(() => {
  'use strict';
  const locale = document.querySelector('meta[name="ci-locale"]')?.content || 'vi';
  const STR = {
    vi: { noData:'Chưa có dữ liệu',notAvailable:'Không có',processing:'Đang chạy',queued:'Đang chờ',done:'Hoàn thành',failed:'Thất bại',yes:'Đã lưu',save:'Lưu sách',remove:'Bỏ lưu',details:'Chi tiết',source:'Xem nguồn',records:'bản ghi',book:'sách',pages:'trang',last:'Cập nhật',error:'Đã xảy ra lỗi',retry:'Thử lại', filterName:'Tên bộ lọc:', filterSaved:'Đã lưu bộ lọc', saved:'Đã lưu',loading:'Đang tải...',goLogin:'Phiên hết hạn. Vui lòng đăng nhập lại.',logout:'Bạn có muốn đăng xuất?',confirmed:'Cập nhật thành công.',emptyBooks:'Không tìm thấy sách phù hợp.',emptyCollection:'Chưa có sách. Hãy chạy crawler để thu thập dữ liệu thật.',invalidPrice:'Giá GBP từ 0 đến 9999,99 với tối đa 2 số thập phân.',invalidRange:'Giá thấp nhất không được lớn hơn giá cao nhất.',stop:'Đang thu thập',start:'Bắt đầu thu thập',stars:'sao',completedWithErrors:'Hoàn thành có cảnh báo',noNotifications:'Chưa có thông báo thay đổi giá.',priceDecreased:'Giá giảm',priceIncreased:'Giá tăng',markRead:'Đánh dấu đã đọc',openBook:'Xem sách',markAllRead:'Đánh dấu đã đọc'},
    en: { noData:'No data yet',notAvailable:'Not available',processing:'Running',queued:'Queued',done:'Completed',failed:'Failed',yes:'Saved',save:'Save book',remove:'Remove',details:'Details',source:'View source',records:'records',book:'books',pages:'pages',last:'Updated',error:'Something went wrong',retry:'Try again', filterName:'Filter name:', filterSaved:'Filter saved', saved:'Saved',loading:'Loading...',goLogin:'Session expired. Sign in again.',logout:'Sign out?',confirmed:'Changes saved.',emptyBooks:'No books match your filters.',emptyCollection:'No books yet. Start a real crawl to collect data.',invalidPrice:'Enter GBP prices from 0 to 9999.99, up to 2 decimal places.',invalidRange:'Minimum price cannot exceed maximum price.',stop:'Crawl in progress',start:'Start crawling',stars:'stars',completedWithErrors:'Completed with warnings',noNotifications:'No price change notifications yet.',priceDecreased:'Price decreased',priceIncreased:'Price increased',markRead:'Mark as read',openBook:'View book',markAllRead:'Mark all read'}
  };
  const t = key => STR[locale]?.[key] || STR.vi[key] || key;
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('mobile-overlay');
  const menu = document.getElementById('mobile-menu');
  const toggleMenu = isOpen => {
    if (!sidebar || !overlay || !menu) return;
    sidebar.classList.toggle('open', isOpen); overlay.hidden=!isOpen;
    menu.setAttribute('aria-expanded',String(isOpen));
  };
  menu?.addEventListener('click',()=>toggleMenu(!sidebar.classList.contains('open')));
  overlay?.addEventListener('click',()=>toggleMenu(false));
  document.addEventListener('keydown',e=>{ if(e.key==='Escape') toggleMenu(false); });
  const csrf = () => document.querySelector('meta[name="csrf-token"]')?.content || '';
  async function fetchJSON(path, options={}) {
    const headers = {Accept:'application/json', ...(options.body?{'Content-Type':'application/json'}:{}),
      ...(['POST','PATCH','PUT','DELETE'].includes(String(options.method||'GET').toUpperCase())?{'X-CSRF-Token':csrf()}:{}), ...(options.headers||{})};
    const response = await fetch(path,{credentials:'same-origin',cache:'no-store',...options,headers});
    let data;
    try { data=await response.json(); } catch {throw new Error('Invalid server response');}
    if (!response.ok) {
      const error=new Error(data?.error?.message || `Request failed (${response.status})`);
      error.status=response.status;error.code=data?.error?.code||'UNKNOWN_ERROR';
      if (error.status===401 && !location.pathname.startsWith('/login')) {
        toast(t('goLogin'),'error');
      }
      throw error;
    }
    return data;
  }
  function toast(message,type='info') {
    const region=document.getElementById('toast-region');if(!region)return;
    const item=document.createElement('div');item.className=`toast ${type}`;item.setAttribute('role','status');
    item.textContent=String(message);region.append(item);setTimeout(()=>item.remove(),4800);
  }
  function formatDate(value,withTime=true) {
    if(!value)return t('notAvailable');const date=new Date(value);if(!Number.isFinite(date.getTime()))return t('notAvailable');
    return new Intl.DateTimeFormat(locale==='vi'?'vi-VN':'en-GB',withTime?{day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit'}:{day:'2-digit',month:'short',year:'numeric'}).format(date);
  }
  const pounds=pence=>new Intl.NumberFormat(locale==='vi'?'vi-VN':'en-GB',{style:'currency',currency:'GBP'}).format(Number(pence)/100);
  const notificationCenter=document.getElementById('notification-center');
  if(notificationCenter){
    const toggle=document.getElementById('notification-toggle');
    const panel=document.getElementById('notification-panel');
    const count=document.getElementById('notification-count');
    const list=document.getElementById('notification-list');
    const markAll=document.getElementById('notification-read-all');
    const showEmpty=message=>{const empty=document.createElement('p');empty.className='notification-empty';empty.textContent=message;list.replaceChildren(empty);};
    const updateCount=value=>{
      const unread=Math.max(0,Number(value)||0);
      count.hidden=unread===0;
      count.textContent=unread>99?'99+':String(unread);
      toggle.setAttribute('aria-label',`${t('notifications')}${unread?`: ${unread}`:''}`);
      markAll.hidden=unread===0;
    };
    const loadNotifications=async()=>{
      try{
        const data=await fetchJSON('/api/notifications');
        updateCount(data.unread_count);
        list.replaceChildren();
        if(!data.items.length){showEmpty(t('noNotifications'));return;}
        for(const item of data.items){
          const entry=document.createElement('article');
          entry.className=`notification-item${item.read_at?'':' unread'}`;
          const heading=document.createElement('div');
          heading.className='notification-item-heading';
          const title=document.createElement('strong');
          title.textContent=item.title;
          const detail=document.createElement('p');
          const decreased=Number(item.new_price_pence)<Number(item.old_price_pence);
          detail.textContent=`${t(decreased?'priceDecreased':'priceIncreased')}: ${pounds(item.old_price_pence)} → ${pounds(item.new_price_pence)}`;
          const date=document.createElement('time');
          date.className='notification-date';
          date.dateTime=item.created_at;
          date.textContent=formatDate(item.created_at);
          const actions=document.createElement('div');
          actions.className='notification-item-actions';
          const bookLink=document.createElement('a');
          bookLink.href=`/books?q=${encodeURIComponent(item.title)}`;
          bookLink.textContent=t('openBook');
          actions.append(bookLink);
          if(!item.read_at){
            const readButton=document.createElement('button');
            readButton.type='button';
            readButton.dataset.notificationRead=item.id;
            readButton.textContent=t('markRead');
            actions.append(readButton);
          }
          heading.append(title);
          entry.append(heading,detail,date,actions);
          list.append(entry);
        }
      }catch(error){
        showEmpty(error.message);
        toast(error.message,'error');
      }
    };
    toggle.addEventListener('click',()=>{
      const isOpen=toggle.getAttribute('aria-expanded')==='true';
      toggle.setAttribute('aria-expanded',String(!isOpen));
      panel.hidden=isOpen;
      if(!isOpen)loadNotifications();
    });
    list.addEventListener('click',async event=>{
      const button=event.target.closest('[data-notification-read]');
      if(!button)return;
      button.disabled=true;
      try{
        await fetchJSON(`/api/notifications/${button.dataset.notificationRead}/read`,{method:'PATCH',body:'{}'});
        await loadNotifications();
      }catch(error){
        button.disabled=false;
        toast(error.message,'error');
      }
    });
    markAll.addEventListener('click',async()=>{
      markAll.disabled=true;
      try{
        await fetchJSON('/api/notifications/read',{method:'PATCH',body:'{}'});
        await loadNotifications();
      }catch(error){
        toast(error.message,'error');
      }finally{
        markAll.disabled=false;
      }
    });
    document.addEventListener('click',event=>{
      if(!notificationCenter.contains(event.target)){
        panel.hidden=true;
        toggle.setAttribute('aria-expanded','false');
      }
    });
    document.addEventListener('keydown',event=>{
      if(event.key==='Escape'){
        panel.hidden=true;
        toggle.setAttribute('aria-expanded','false');
      }
    });
    loadNotifications();
  }
  function setTheme(theme){
    document.documentElement.dataset.theme=theme;
    document.documentElement.style.colorScheme=theme==='dark'?'dark':theme==='light'?'light':'';
    try{localStorage.setItem('ci-theme',theme);}catch{}
  }
  if (!document.body.classList.contains('is-workspace')) {
    try{setTheme(localStorage.getItem('ci-theme')||'system');}catch{}
  }
  document.getElementById('theme-quick')?.addEventListener('click',async()=>{
    const current=document.documentElement.dataset.theme;
    const next=(current==='dark')?'light':'dark';
    const inWorkspace=document.body.classList.contains('is-workspace');
    try{if(inWorkspace)await fetchJSON('/api/me/preferences',{method:'PATCH',body:JSON.stringify({theme:next})});setTheme(next);}
    catch(e){toast(e.message,'error');}
  });
  document.querySelectorAll('[data-language-switch]').forEach(b=>b.addEventListener('click',async()=>{
    const next=locale==='vi'?'en':'vi';
    if(!document.body.classList.contains('is-workspace')){
      const url=new URL(location.href);url.searchParams.set('lang',next);location.assign(url.pathname+url.search+url.hash);return;
    }
    try{await fetchJSON('/api/me/preferences',{method:'PATCH',body:JSON.stringify({locale:next})});location.reload();}
    catch(e){toast(e.message,'error');}
  }));
  window.CrawlInsight={fetchJSON,toast,formatDate,pounds,t,locale,setTheme};
})();
