(() => {
  'use strict';
  const {fetchJSON,formatDate,toast}=window.CrawlInsight;
  const body=document.getElementById('admin-users-body');
  const errorBox=document.getElementById('admin-users-error');
  const search=document.getElementById('admin-user-search');
  const count=document.getElementById('admin-user-count');
  const pageLabel=document.getElementById('admin-users-page');
  const previous=document.getElementById('admin-users-previous');
  const next=document.getElementById('admin-users-next');
  let page=1;
  let totalPages=1;
  let currentUserId=null;
  const t=window.CrawlInsight.t;
  const text=(tag,value,className='')=>{
    const cell=document.createElement(tag);
    if(className)cell.className=className;
    cell.textContent=value??'—';
    return cell;
  };
  const load=async()=>{
    errorBox.hidden=true;
    try{
      if(currentUserId===null){
        const identity=await fetchJSON('/api/auth/me');
        currentUserId=Number(identity.user?.id);
      }
      const data=await fetchJSON(`/api/admin/users?page=${page}&q=${encodeURIComponent(search.value.trim())}`);
      body.replaceChildren();
      if(!data.items.length){
        const row=document.createElement('tr');
        const cell=text('td',t('no_users'));
        cell.colSpan=8;row.append(cell);body.append(row);
      }
      for(const user of data.items){
        const row=document.createElement('tr');
        row.append(text('td',user.id),text('td',user.full_name),text('td',user.email));
        row.append(text('td',user.role==='admin'?t('admin_role'):t('user_role'),'admin-role'));
        row.append(text('td',user.is_active?t('active'):t('inactive'),`admin-state${user.is_active?'':' inactive'}`));
        row.append(text('td',formatDate(user.created_at,false)),text('td',formatDate(user.last_login_at)));
        const actions=document.createElement('td');
        const actionGroup=document.createElement('div');
        actionGroup.className='admin-actions';
        const isSelf=Number(user.id)===currentUserId;
        const state=document.createElement('button');
        state.type='button';state.disabled=isSelf;
        state.textContent=user.is_active?t('deactivate'):t('activate');
        state.addEventListener('click',()=>updateUser(user.id,{is_active:!user.is_active}));
        const role=document.createElement('button');
        role.type='button';role.disabled=isSelf;
        role.textContent=user.role==='admin'?t('make_user'):t('make_admin');
        role.addEventListener('click',()=>updateUser(user.id,{role:user.role==='admin'?'user':'admin'}));
        actionGroup.append(state,role);actions.append(actionGroup);row.append(actions);body.append(row);
      }
      count.textContent=`${data.total} ${t('users')}`;
      totalPages=Math.max(data.total_pages,1);
      pageLabel.textContent=`${t('page')} ${page} / ${totalPages}`;
      previous.disabled=page<=1;next.disabled=page>=totalPages;
    }catch(exception){
      errorBox.textContent=exception.message;errorBox.hidden=false;
    }
  };
  const updateUser=async(userId,payload)=>{
    try{
      await fetchJSON(`/api/admin/users/${userId}`,{method:'PATCH',body:JSON.stringify(payload)});
      toast(t('confirmed'),'success');
      await load();
    }catch(exception){toast(exception.message,'error');}
  };
  let timer;
  search.addEventListener('input',()=>{
    clearTimeout(timer);
    timer=setTimeout(()=>{page=1;load();},250);
  });
  previous.addEventListener('click',()=>{if(page>1){page-=1;load();}});
  next.addEventListener('click',()=>{if(page<totalPages){page+=1;load();}});
  load();
})();
