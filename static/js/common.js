/* Shared API, theme, language and navigation. Never set innerHTML from server responses. */
(() => {
  'use strict';
  const locale = document.querySelector('meta[name="ci-locale"]')?.content || 'vi';
  const STR = {
    vi: { noData:'Chưa có dữ liệu',notAvailable:'Không có',processing:'Đang chạy',queued:'Đang chờ',done:'Hoàn thành',failed:'Thất bại',yes:'Đã lưu',save:'Lưu sách',remove:'Bỏ lưu',details:'Chi tiết',source:'Xem nguồn',records:'bản ghi',book:'sách',pages:'trang',last:'Cập nhật',error:'Đã xảy ra lỗi',retry:'Thử lại', filterName:'Tên bộ lọc:', filterSaved:'Đã lưu bộ lọc', saved:'Đã lưu',loading:'Đang tải...',goLogin:'Phiên hết hạn. Vui lòng đăng nhập lại.',logout:'Bạn có muốn đăng xuất?',confirmed:'Cập nhật thành công.',emptyBooks:'Không tìm thấy sách phù hợp.',emptyCollection:'Chưa có sách. Hãy chạy crawler để thu thập dữ liệu thật.',invalidPrice:'Giá GBP từ 0 đến 9999,99 với tối đa 2 số thập phân.',invalidRange:'Giá thấp nhất không được lớn hơn giá cao nhất.',stop:'Đang thu thập',start:'Bắt đầu thu thập',stars:'sao',completedWithErrors:'Hoàn thành có cảnh báo',noNotifications:'Chưa có thông báo.',crawlQueued:'đã được thêm vào hàng đợi',crawlRunning:'đang được thu thập',crawlCompleted:'đã hoàn tất',crawlFailed:'đã thất bại',viewHistory:'Xem lịch sử crawl',priceDecreased:'Giá giảm',priceIncreased:'Giá tăng',markRead:'Đánh dấu đã đọc',openBook:'Xem sách',markAllRead:'Đánh dấu đã đọc',resetBooks:'Đặt lại sách',resetConfirm:'Bạn có chắc chắn muốn xóa toàn bộ sách đã crawl? Thao tác này sẽ xóa tất cả sách và lịch sử crawl của bạn.',resetSuccess:'Đã đặt lại dữ liệu sách thành công.',deleteCrawl:'Xóa',deleteCrawlConfirm:'Bạn có chắc chắn muốn xóa lịch sử crawl #{id}? Sách đã thu thập sẽ được giữ lại.',crawlDeleted:'Đã xóa lịch sử crawl.',crawlActiveCannotDelete:'Không thể xóa lượt crawl đang hoạt động.',avatarInvalidFile:'Hãy chọn ảnh PNG, JPEG hoặc WebP không lớn hơn 12 MB.',avatarSaved:'Đã cập nhật ảnh đại diện.',avatarLoadFailed:'Không tải được ảnh đại diện hiện tại.'},
    en: { noData:'No data yet',notAvailable:'Not available',processing:'Running',queued:'Queued',done:'Completed',failed:'Failed',yes:'Saved',save:'Save book',remove:'Remove',details:'Details',source:'View source',records:'records',book:'books',pages:'pages',last:'Updated',error:'Something went wrong',retry:'Try again', filterName:'Filter name:', filterSaved:'Filter saved', saved:'Saved',loading:'Loading...',goLogin:'Session expired. Sign in again.',logout:'Sign out?',confirmed:'Changes saved.',emptyBooks:'No books match your filters.',emptyCollection:'No books yet. Start a real crawl to collect data.',invalidPrice:'Enter GBP prices from 0 to 9999.99, up to 2 decimal places.',invalidRange:'Minimum price cannot exceed maximum price.',stop:'Crawl in progress',start:'Start crawling',stars:'stars',completedWithErrors:'Completed with warnings',noNotifications:'No notifications yet.',crawlQueued:'was added to the queue',crawlRunning:'is being crawled',crawlCompleted:'completed',crawlFailed:'failed',viewHistory:'View crawl history',priceDecreased:'Price decreased',priceIncreased:'Price increased',markRead:'Mark as read',openBook:'View book',markAllRead:'Mark all read',resetBooks:'Reset books',resetConfirm:'Are you sure you want to reset all crawled books? This will delete all your books and crawl history.',resetSuccess:'Successfully reset all crawled books.',deleteCrawl:'Delete',deleteCrawlConfirm:'Are you sure you want to delete crawl history #{id}? Collected books will be kept.',crawlDeleted:'Crawl history deleted.',crawlActiveCannotDelete:'An active crawl cannot be deleted.',avatarInvalidFile:'Choose a PNG, JPEG, or WebP image no larger than 12 MB.',avatarSaved:'Profile picture updated.',avatarLoadFailed:'Could not load the current profile picture.'}
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
  sidebar?.querySelectorAll('a').forEach(a=>{
    a.addEventListener('click',()=>{ if(window.innerWidth<=768) toggleMenu(false); });
  });
  document.querySelectorAll('[data-reveal]').forEach(b=>{
    b.addEventListener('click',()=>{
      const input=document.getElementById(b.dataset.reveal);
      if(!input) return;
      const isPassword=input.type==='password';
      input.type=isPassword?'text':'password';
      b.classList.toggle('revealed',isPassword);
      const eye=b.querySelector('.icon-eye');
      const eyeOff=b.querySelector('.icon-eye-off');
      if(eye&&eyeOff){
        eye.hidden=isPassword;
        eyeOff.hidden=!isPassword;
      }
      const isVi=locale==='vi'||document.querySelector('meta[name="ci-locale"]')?.content==='vi';
      b.setAttribute('aria-label',isPassword?(isVi?'Ẩn mật khẩu':'Hide password'):(isVi?'Hiện mật khẩu':'Show password'));
    });
  });
  const csrf = () => document.querySelector('meta[name="csrf-token"]')?.content || '';
  async function fetchJSON(path, options={}) {
    const isFormData = options.body instanceof FormData;
    const headers = {Accept:'application/json', ...(options.body && !isFormData?{'Content-Type':'application/json'}:{}),
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
  let refreshNotifications=()=>{};
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
          const isCrawl=item.kind==='crawl';
          const entry=document.createElement('article');
          entry.className=`notification-item${item.read_at?'':' unread'}`;
          const heading=document.createElement('div');
          heading.className='notification-item-heading';
          const title=document.createElement('strong');
          title.textContent=item.title;
          const detail=document.createElement('p');
          if(isCrawl){
            const state=String(item.status||'').toLowerCase();
            detail.textContent=`${t(`crawl${state[0]?.toUpperCase()}${state.slice(1)}`)} · ${item.source_name}`;
          }else{
            const decreased=Number(item.new_price_pence)<Number(item.old_price_pence);
            detail.textContent=`${t(decreased?'priceDecreased':'priceIncreased')}: ${pounds(item.old_price_pence)} → ${pounds(item.new_price_pence)}`;
          }
          const date=document.createElement('time');
          date.className='notification-date';
          date.dateTime=item.created_at;
          date.textContent=formatDate(item.created_at);
          const actions=document.createElement('div');
          actions.className='notification-item-actions';
          const bookLink=document.createElement('a');
          bookLink.href=isCrawl?'/history':`/books?q=${encodeURIComponent(item.title)}`;
          bookLink.textContent=t(isCrawl?'viewHistory':'openBook');
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
    refreshNotifications=loadNotifications;
  }
  function isDarkTheme(theme){
    if(theme==='dark')return true;
    if(theme==='light')return false;
    return window.matchMedia&&window.matchMedia('(prefers-color-scheme: dark)').matches;
  }
  function syncThemeToggleInputs(theme){
    const activeTheme=theme||document.documentElement.dataset.theme||'system';
    const dark=isDarkTheme(activeTheme);
    document.querySelectorAll('.theme-toggle-input').forEach(input=>{
      input.checked=dark;
    });
  }
  function setTheme(theme){
    document.documentElement.dataset.theme=theme;
    document.documentElement.style.colorScheme=theme==='dark'?'dark':theme==='light'?'light':'';
    try{localStorage.setItem('ci-theme',theme);}catch{}
    syncThemeToggleInputs(theme);
  }
  if (!document.body.classList.contains('is-workspace')) {
    try{setTheme(localStorage.getItem('ci-theme')||'system');}catch{}
  } else {
    syncThemeToggleInputs(document.documentElement.dataset.theme);
  }
  if(window.matchMedia){
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change',()=>{
      if((document.documentElement.dataset.theme||'system')==='system'){
        syncThemeToggleInputs('system');
      }
    });
  }
  document.querySelectorAll('.theme-toggle-input').forEach(input=>{
    input.addEventListener('change',async()=>{
      const next=input.checked?'dark':'light';
      const inWorkspace=document.body.classList.contains('is-workspace');
      try{
        if(inWorkspace)await fetchJSON('/api/me/preferences',{method:'PATCH',body:JSON.stringify({theme:next})});
        setTheme(next);
      }catch(e){
        toast(e.message,'error');
        syncThemeToggleInputs(document.documentElement.dataset.theme);
      }
    });
  });
  document.getElementById('theme-quick')?.addEventListener('click',async()=>{
    const current=document.documentElement.dataset.theme;
    const next=(current==='dark')?'light':'dark';
    const inWorkspace=document.body.classList.contains('is-workspace');
    try{if(inWorkspace)await fetchJSON('/api/me/preferences',{method:'PATCH',body:JSON.stringify({theme:next})});setTheme(next);}
    catch(e){toast(e.message,'error');}
  });
  document.querySelectorAll('[data-language-switch]').forEach(b=>b.addEventListener('click',async()=>{
    const next=locale==='vi'?'en':'vi';
    if(!document.body.classList.contains('is-authenticated')){
      const url=new URL(location.href);url.searchParams.set('lang',next);location.assign(url.pathname+url.search+url.hash);return;
    }
    try{await fetchJSON('/api/me/preferences',{method:'PATCH',body:JSON.stringify({locale:next})});location.reload();}
    catch(e){toast(e.message,'error');}
  }));
  const galaxyScene=document.querySelector('[data-galaxy-scene]');
  const galaxyShip=galaxyScene?.querySelector('[data-galaxy-ship]');
  const reducedMotion=window.matchMedia('(prefers-reduced-motion: reduce)');
  if(galaxyScene&&galaxyShip&&!reducedMotion.matches){
    galaxyScene.addEventListener('pointerenter',event=>{
      if(event.pointerType==='mouse')galaxyScene.classList.add('is-exploring');
    });
    galaxyScene.addEventListener('pointermove',event=>{
      if(event.pointerType!=='mouse')return;
      const bounds=galaxyScene.getBoundingClientRect();
      const x=event.clientX-bounds.left;
      const y=event.clientY-bounds.top;
      const tiltX=((x/bounds.width)-.5)*8;
      const tiltY=((y/bounds.height)-.5)*-8;
      galaxyScene.style.setProperty('--ship-x',`${x}px`);
      galaxyScene.style.setProperty('--ship-y',`${y}px`);
      galaxyScene.style.setProperty('--tilt-x',`${tiltX}deg`);
      galaxyScene.style.setProperty('--tilt-y',`${tiltY}deg`);
    });
    galaxyScene.addEventListener('pointerleave',()=>{
      galaxyScene.classList.remove('is-exploring');
      galaxyScene.style.setProperty('--tilt-x','0deg');
      galaxyScene.style.setProperty('--tilt-y','0deg');
    });
  }
  window.CrawlInsight={fetchJSON,toast,formatDate,pounds,t,locale,setTheme,refreshNotifications};
})();
