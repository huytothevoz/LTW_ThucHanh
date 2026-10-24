(() => {
 'use strict';
 const app=window.CrawlInsight;
 const form=document.getElementById('auth-form'); if(!form)return;
 const mode=form.dataset.mode;
 const error=document.getElementById('auth-error');const success=document.getElementById('auth-success');
 const button=document.getElementById('auth-submit');

 form.addEventListener('submit',async e=>{
   e.preventDefault();error.hidden=true;success.hidden=true;button.disabled=true;
   const payload={};let path='';
   if(mode==='login'){path='/api/auth/login';payload.email=document.getElementById('auth-email').value;payload.password=document.getElementById('auth-password').value;}
   if(mode==='register'){path='/api/auth/register';payload.full_name=document.getElementById('full-name').value;payload.email=document.getElementById('auth-email').value;payload.password=document.getElementById('auth-password').value;}
   if(mode==='forgot'){path='/api/auth/request-reset';payload.email=document.getElementById('auth-email').value;}
   if(mode==='reset'){path='/api/auth/reset-password';payload.token=form.dataset.resetToken;payload.password=document.getElementById('auth-password').value;}
   if(['register','reset'].includes(mode)&&payload.password!==document.getElementById('confirm-password').value){error.textContent=app.locale==='vi'?'Xác nhận mật khẩu không trùng khớp.':'Passwords do not match.';error.hidden=false;button.disabled=false;return;}
   if(['register','reset'].includes(mode)&&(!/\d/.test(payload.password)||!/[A-Za-z]/.test(payload.password)||payload.password.length<10)){error.textContent=app.locale==='vi'?'Mật khẩu cần từ 10 ký tự, gồm chữ và số.':'Password needs 10+ characters, letters and numbers.';error.hidden=false;button.disabled=false;return;}
   try{
     const data=await app.fetchJSON(path,{method:'POST',body:JSON.stringify(payload)});
     if(['login','register'].includes(mode)){location.assign('/workspace');return;}
     if(mode==='reset'){success.textContent=app.locale==='vi'?'Đặt lại mật khẩu thành công. Chuyển đến đăng nhập...':'Password reset. Redirecting to sign-in...';success.hidden=false;setTimeout(()=>location.assign('/login'),1400);return;}
     success.textContent=data.message;success.hidden=false;
     if(data.local_test_link){const link=document.createElement('a');link.href=data.local_test_link;link.textContent=app.locale==='vi'?'Liên kết khôi phục (chỉ để kiểm thử local)':'Local testing reset link';link.className='local-reset-link';success.append(document.createElement('br'),link);}
   }catch(ex){error.textContent=ex.message;error.hidden=false;}
   finally{button.disabled=false;}
 });
})();
