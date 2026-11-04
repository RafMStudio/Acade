import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "npm:@supabase/supabase-js@2";

const allowedOrigins=new Set(['https://eduitqan.com','https://www.eduitqan.com']);
const corsFor=(req:Request)=>{const origin=req.headers.get('Origin')||'';return {'Access-Control-Allow-Origin':allowedOrigins.has(origin)?origin:'https://eduitqan.com','Vary':'Origin','Access-Control-Allow-Headers':'authorization, x-client-info, apikey, content-type','Access-Control-Allow-Methods':'POST, OPTIONS'};};
const reply=(req:Request,status:number,body:unknown)=>new Response(JSON.stringify(body),{status,headers:{...corsFor(req),'Content-Type':'application/json','Cache-Control':'no-store'}});
const protectedRoles=['SystemAdmin','HOD','APU','VDAA'];

Deno.serve(async(req:Request)=>{
  const origin=req.headers.get('Origin')||'';
  if(origin&&!allowedOrigins.has(origin))return reply(req,403,{error:'Origin not allowed'});
  if(req.method==='OPTIONS')return new Response('ok',{headers:corsFor(req)});
  if(req.method!=='POST')return reply(req,405,{error:'Method not allowed'});
  const token=(req.headers.get('Authorization')||'').replace(/^Bearer\s+/i,'').trim();
  if(!token)return reply(req,401,{error:'Authentication required'});
  const supabase=createClient(Deno.env.get('SUPABASE_URL')!,Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!,{auth:{persistSession:false}});
  const {data:au,error:authError}=await supabase.auth.getUser(token);
  if(authError||!au.user)return reply(req,401,{error:'Invalid or expired session'});
  const {data:caller}=await supabase.from('profiles').select('id,role,active,department').eq('id',au.user.id).single();
  if(!caller?.active||!['SystemAdmin','HOD'].includes(caller.role))return reply(req,403,{error:'Not authorized'});
  let b:any;try{b=await req.json()}catch{return reply(req,400,{error:'Invalid request'})}
  const userId=String(b.user_id||'').trim(),action=String(b.action||'update');
  if(!userId)return reply(req,400,{error:'user_id required'});
  const {data:target}=await supabase.from('profiles').select('id,email,role,active,department,limit_program_access').eq('id',userId).maybeSingle();
  if(!target)return reply(req,404,{error:'User not found'});
  if(target.role==='SystemAdmin'&&caller.role!=='SystemAdmin')return reply(req,403,{error:'Only System Administrator can manage a System Administrator'});
  if(['APU','VDAA'].includes(target.role)&&caller.role!=='SystemAdmin')return reply(req,403,{error:'Only System Administrator can manage APU or VDAA supervisors'});
  if(caller.role==='HOD'){
    if(protectedRoles.includes(target.role))return reply(req,403,{error:'HOD cannot manage leadership or global supervisor accounts'});
    if(!caller.department||caller.department!==target.department)return reply(req,403,{error:'You may only manage users in your department'});
    const {data:mine}=await supabase.from('program_memberships').select('program_id').eq('user_id',caller.id).eq('role','HOD').eq('active',true);
    if(!mine?.length)return reply(req,403,{error:'You do not have an active HOD assignment'});
  }
  if(action==='status'){
    const active=Boolean(b.active);
    if(userId===caller.id&&!active)return reply(req,400,{error:'You cannot deactivate your own account'});
    if(target.role==='SystemAdmin'&&caller.role==='SystemAdmin'&&!active){
      const {count}=await supabase.from('profiles').select('id',{count:'exact',head:true}).eq('role','SystemAdmin').eq('active',true);
      if((count||0)<=1)return reply(req,400,{error:'The last active System Administrator cannot be deactivated'});
    }
    const {error:profileError}=await supabase.from('profiles').update({active}).eq('id',userId);
    if(profileError)return reply(req,500,{error:profileError.message});
    if(caller.role==='HOD'){
      const {data:programs}=await supabase.from('academic_programs').select('id').eq('department',caller.department);
      const ids=(programs||[]).map((p:any)=>p.id);
      if(ids.length)await supabase.from('program_memberships').update({active}).eq('user_id',userId).in('program_id',ids);
    }else{
      await supabase.from('program_memberships').update({active}).eq('user_id',userId);
    }
    if(!active)await supabase.auth.admin.signOut(userId,'global');
    await supabase.from('audit_log').insert({actor_id:caller.id,action:active?'reactivate_user':'deactivate_user',entity_type:'profile',entity_id:userId,details:{department:target.department,email:target.email,role:target.role}});
    return reply(req,200,{ok:true,active});
  }
  if(action==='assign'){
    if(caller.role!=='SystemAdmin')return reply(req,403,{error:'Only System Administrator can change program assignments'});
    if(['APU','VDAA'].includes(target.role))return reply(req,400,{error:'APU and VDAA are global read-only supervisors and cannot be assigned to a program'});
    const programId=String(b.program_id||'').trim();if(!programId)return reply(req,400,{error:'program_id required'});
    const role=String(b.role||'');if(!['HOD','Coordinator','Instructor'].includes(role))return reply(req,400,{error:'Invalid role'});
    const {data:program}=await supabase.from('academic_programs').select('id,department,status').eq('id',programId).maybeSingle();
    if(!program||program.status!=='Open'||program.department!==target.department)return reply(req,400,{error:'Program must be open and belong to the user department'});
    await supabase.from('program_memberships').upsert({program_id:programId,user_id:userId,role,active:true,created_by:caller.id},{onConflict:'program_id,user_id'});
    await supabase.from('profiles').update({role,default_program_id:programId,active:true,limit_program_access:true}).eq('id',userId);
    await supabase.auth.admin.updateUserById(userId,{app_metadata:{role}});
    await supabase.from('audit_log').insert({actor_id:caller.id,action:'assign_user_program',entity_type:'profile',entity_id:userId,details:{program_id:programId,role}});
    return reply(req,200,{ok:true});
  }
  return reply(req,400,{error:'Unsupported action'});
});