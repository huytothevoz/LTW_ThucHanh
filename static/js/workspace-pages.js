/* Dedicated page controllers. DOM building uses textContent for all fetched data. */
(() => {
 'use strict';
 const {fetchJSON,toast,formatDate,pounds,t,locale}=window.CrawlInsight;
 const $=id=>document.getElementById(id);
 const text=(tag,cls,value)=>{const el=document.createElement(tag);el.className=cls;el.textContent=String(value);return el;};
 const el=(tag,cls)=>{const e=document.createElement(tag);e.className=cls;return e;};
 const sourceUrl=value=>{try{const u=new URL(value);return u.protocol==='https:'&&u.hostname==='books.toscrape.com'&&!u.username&&!u.password?u.href:null;}catch{return null;}};

 async function savedPage(){
   let page=1,totalPages=0;
   async function load(){
     try{
       const data=await fetchJSON(`/api/bookmarks?page=${page}`);totalPages=data.total_pages;
       $('saved-loading').hidden=true;$('saved-empty').hidden=data.total>0;$('saved-result-count').textContent=`${data.total} ${t('records')}`;
       $('saved-grid').replaceChildren();
       for(const book of data.items){
         const card=el('article','saved-card');const cover=el('div','saved-cover');
         const imgUrl=sourceUrl(book.image_url);if(imgUrl){const img=document.createElement('img');img.src=imgUrl;img.loading='lazy';img.alt=book.title;img.referrerPolicy='no-referrer';cover.append(img);}else cover.append(text('span','saved-placeholder','📖'));
         const info=el('div','saved-info');info.append(text('span','book-category',book.category),text('h3','',book.title),text('strong','book-price',pounds(book.price_pence)));
         const buttons=el('div','saved-actions');const original=document.createElement('a');original.className='outlined-action';original.textContent=t('source')+' ↗';
         const u=sourceUrl(book.source_url);if(u){original.href=u;original.target='_blank';original.rel='noopener noreferrer';}
         const remove=document.createElement('button');remove.className='danger-link';remove.textContent=t('remove');remove.addEventListener('click',async()=>{
           try{await fetchJSON(`/api/bookmarks/${book.id}`,{method:'DELETE'});toast(t('confirmed'),'success');load();}catch(e){toast(e.message,'error');}
         });buttons.append(original,remove);info.append(buttons);card.append(cover,info);$('saved-grid').append(card);
       }
       $('saved-pagination').hidden=data.total_pages<=1;$('saved-page').textContent=`${page} / ${Math.max(data.total_pages,1)}`;
       $('saved-prev').disabled=page<=1;$('saved-next').disabled=page>=totalPages;
     }catch(e){$('saved-loading').textContent=e.message;toast(e.message,'error');}
   }
   $('saved-prev').addEventListener('click',()=>{if(page>1){page--;load();}});
   $('saved-next').addEventListener('click',()=>{if(page<totalPages){page++;load();}});
   load();
 }

 async function historyPage(){
   const tbody=$('history-tbody');
   try{
     const data=await fetchJSON('/api/history');tbody.replaceChildren();
     if(!data.items.length){const row=document.createElement('tr');const td=document.createElement('td');td.colSpan=8;td.textContent=locale==='vi'?'Chưa có phiên nào.':'No sessions yet.';row.append(td);tbody.append(row);return;}
     for(const job of data.items){
       const row=document.createElement('tr');
       const values=[`#${job.id}`,job.status,formatDate(job.created_at),`${job.catalogue_pages_done}/${job.max_pages}`,job.books_found,job.items_saved,job.error_count];
       values.forEach((v,i)=>{const td=text('td',i===1?`status-text s-${String(v).toLowerCase()}`:'',v);row.append(td);});
       const button=document.createElement('button');button.type='button';button.className='text-action';button.textContent=t('details')+' →';
       button.addEventListener('click',async()=>{
         try{
           const data=await fetchJSON(`/api/jobs/${job.id}`);const detail=$('history-detail');detail.hidden=false;detail.replaceChildren();
           detail.append(text('h3','','Crawl #'+job.id),text('p','',`${t('status')}: ${data.job.status} · ${t('found')}: ${data.job.books_found} · ${t('errors')}: ${data.job.error_count}`));
           (data.events||[]).forEach(ev=>detail.append(text('p','event-row',`${formatDate(ev.created_at)} · ${ev.level} · ${ev.message}`)));
           detail.scrollIntoView({behavior:'smooth',block:'nearest'});
         }catch(e){toast(e.message,'error');}
       });const cell=document.createElement('td');cell.append(button);row.append(cell);tbody.append(row);
     }
   }catch(e){tbody.replaceChildren();$('history-error').textContent=e.message;$('history-error').hidden=false;}
 }

 async function analyticsPage(){
   try{
     const data=await fetchJSON('/api/analytics');const p=data.prices;
     $('an-total').textContent=Number(p.total||0).toLocaleString(locale==='vi'?'vi-VN':'en-GB');
     $('an-min').textContent=p.minimum===null?'—':pounds(p.minimum);
     $('an-max').textContent=p.maximum===null?'—':pounds(p.maximum);
     $('an-avg').textContent=p.average===null?'—':pounds(p.average);
     const chart=$('an-ratings');let ratingTotal=0;chart.replaceChildren();
     const max=Math.max(...data.rating_distribution.map(x=>x.count),1);
     data.rating_distribution.forEach(item=>{ratingTotal+=item.count;const line=el('div','analytics-bar-row');
       line.append(text('span','',`${item.rating} ★`));const track=el('div','analytics-track');const fill=el('span','analytics-fill');fill.style.width=`${(item.count/max)*100}%`;track.append(fill);line.append(track,text('strong','',item.count));chart.append(line);});
     $('an-rating-empty').hidden=ratingTotal!==0;
     const cat=$('an-categories');cat.replaceChildren();const catMax=Math.max(...data.categories.map(x=>x.total_books),1);
     data.categories.forEach(item=>{const row=el('div','category-row');const meta=el('div','category-meta');meta.append(text('strong','',item.category),text('span','',item.total_books));
       const track=el('div','analytics-track');const fill=el('span','analytics-fill');fill.style.width=`${item.total_books/catMax*100}%`;track.append(fill);row.append(meta,track);cat.append(row);});
     $('an-category-empty').hidden=data.categories.length>0;
   }catch(e){toast(e.message,'error');}
 }

 function settingsPage(){
   async function submit(form,endpoint,method,values,after){
     const button=form.querySelector('[type="submit"]');button.disabled=true;
     try{const data=await fetchJSON(endpoint,{method,body:JSON.stringify(values)});toast(t('confirmed'),'success');after?.(data);}catch(e){toast(e.message,'error');}finally{button.disabled=false;}
   }
   $('profile-form').addEventListener('submit',e=>{e.preventDefault();submit(e.currentTarget,'/api/me/profile','PATCH',{full_name:$('profile-name').value},()=>location.reload());});
   $('preferences-form').addEventListener('submit',e=>{e.preventDefault();submit(e.currentTarget,'/api/me/preferences','PATCH',{locale:$('pref-locale').value,theme:$('pref-theme').value,book_layout:$('pref-layout').value},()=>location.reload());});
   $('change-password-form').addEventListener('submit',e=>{e.preventDefault();if($('next-pass').value!==$('next-pass-confirm').value){toast(locale==='vi'?'Xác nhận mật khẩu chưa đúng.':'Passwords do not match.','error');return;}
     submit(e.currentTarget,'/api/me/password','POST',{current_password:$('current-pass').value,new_password:$('next-pass').value},()=>location.assign('/login'));});
   $('logout-settings').addEventListener('click',async()=>{if(!confirm(t('logout')))return;try{await fetchJSON('/api/auth/logout',{method:'POST',body:'{}'});location.assign('/');}catch(e){toast(e.message,'error');}});
 }
 if($('saved-grid'))savedPage();if($('history-tbody'))historyPage();if($('an-ratings'))analyticsPage();if($('profile-form'))settingsPage();
})();
