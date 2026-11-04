import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "npm:@supabase/supabase-js@2";

const allowedOrigins=new Set(['https://eduitqan.com','https://www.eduitqan.com']);
const corsFor=(req:Request)=>{
  const origin=req.headers.get('Origin')||'';
  return {
    'Access-Control-Allow-Origin':allowedOrigins.has(origin)?origin:'https://eduitqan.com',
    'Vary':'Origin',
    'Access-Control-Allow-Headers':'authorization, x-client-info, apikey, content-type',
    'Access-Control-Allow-Methods':'POST, OPTIONS'
  };
};
const reply=(req:Request,status:number,body:unknown)=>new Response(JSON.stringify(body),{status,headers:{...corsFor(req),'Content-Type':'application/json','Cache-Control':'no-store'}});
const allowedPrefixes=['Mr.','Ms.','Dr.'];
const programRoles=['HOD','Coordinator','Instructor'];
const supervisorRoles=['APU','VDAA'];

Deno.serve(async(req:Request)=>{
  const origin=req.headers.get('Origin')||'';
  if(origin && !allowedOrigins.has(origin)) return reply(req,403,{error:'Origin not allowed'});
  if(req.method==='OPTIONS')return new Response('ok',{headers:corsFor(req)});
  if(req.method!=='POST')return reply(req,405,{error:'Method not allowed'});

  const token=(req.headers.get('Authorization')||'').replace(/^Bearer\s+/i,'').trim();
  if(!token)return reply(req,401,{error:'Authentication required'});

  const supabase=createClient(Deno.env.get('SUPABASE_URL')!,Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!,{auth:{persistSession:false}});
  const {data:authData,error:authError}=await supabase.auth.getUser(token);
  if(authError||!authData.user)return reply(req,401,{error:'Invalid or expired session'});

  const {data:caller,error:callerError}=await supabase.from('profiles').select('id,role,active,department').eq('id',authData.user.id).single();
  if(callerError||!caller?.active||!['SystemAdmin','HOD'].includes(caller.role))return reply(req,403,{error:'You cannot add users'});

  let body:any;try{body=await req.json()}catch{return reply(req,400,{error:'Invalid request'})}
  const email=String(body.email||'').trim().toLowerCase();
  const titlePrefix=String(body.title_prefix||body.titlePrefix||'').trim();
  const firstName=String(body.first_name||body.firstName||'').trim();
  const lastName=String(body.last_name||body.lastName||'').trim();
  const requestedDepartment=String(body.department||'').trim();
  const role=String(body.role||'').trim();
  const isSupervisor=supervisorRoles.includes(role);
  const department=isSupervisor?'System Supervision':requestedDepartment;
  const limitProgramAccess=isSupervisor?false:Boolean(body.limit_program_access??body.limitProgramAccess??false);
  const requestedProgramIds=isSupervisor?[]:(Array.isArray(body.program_ids||body.programIds)?[...new Set((body.program_ids||body.programIds).map((x:any)=>String(x||'').trim()).filter(Boolean))]:[]);

  if(!email||!/^\S+@\S+\.\S+$/.test(email))return reply(req,400,{error:'A valid email is required'});
  if(!allowedPrefixes.includes(titlePrefix))return reply(req,400,{error:'Prefix must be Mr., Ms., or Dr.'});
  if(!firstName||!lastName)return reply(req,400,{error:'First name and last name are required'});
  if(![...programRoles,...supervisorRoles].includes(role))return reply(req,400,{error:'Invalid EduItqan role'});
  if(isSupervisor&&caller.role!=='SystemAdmin')return reply(req,403,{error:'Only the System Administrator can create APU or VDAA supervisors'});
  if(!isSupervisor&&!department)return reply(req,400,{error:'Department is required'});
  if(caller.role==='HOD'&&role==='HOD')return reply(req,403,{error:'Only System Administrator can appoint an HOD'});
  if(caller.role==='HOD'&&caller.department!==department)return reply(req,403,{error:'You may only add users to your department'});

  let accessibleProgramIds:string[]=[];
  let defaultProgramId:string|null=null;
  if(!isSupervisor){
    const {data:departmentPrograms,error:programError}=await supabase.from('academic_programs').select('id,department,status').eq('department',department).eq('status','Open');
    if(programError)return reply(req,500,{error:'Could not load department programs'});
    if(!departmentPrograms?.length)return reply(req,400,{error:'This department has no open academic programs'});

    if(caller.role==='HOD'){
      const ids=departmentPrograms.map((p:any)=>p.id);
      const {data:mine}=await supabase.from('program_memberships').select('program_id').eq('user_id',caller.id).eq('role','HOD').eq('active',true).in('program_id',ids);
      if(!mine?.length)return reply(req,403,{error:'You are not assigned as HOD for this department'});
    }

    const validIds=new Set(departmentPrograms.map((p:any)=>p.id));
    if(limitProgramAccess&&requestedProgramIds.length===0)return reply(req,400,{error:'Select at least one academic program when program access is limited'});
    if(requestedProgramIds.some((id:string)=>!validIds.has(id)))return reply(req,400,{error:'One or more selected programs do not belong to this department'});
    accessibleProgramIds=limitProgramAccess?requestedProgramIds:departmentPrograms.map((p:any)=>p.id);
    defaultProgramId=accessibleProgramIds[0]||null;
  }

  const {data:existingProfile,error:existingProfileError}=await supabase.from('profiles').select('id,email,role').eq('email',email).maybeSingle();
  if(existingProfileError)return reply(req,500,{error:'Could not check existing user'});
  let userId=existingProfile?.id||null;
  if(existingProfile?.role==='SystemAdmin')return reply(req,403,{error:'System Administrator accounts cannot be reassigned here'});
  if(caller.role==='HOD'&&supervisorRoles.includes(existingProfile?.role||''))return reply(req,403,{error:'HOD cannot manage global supervisor accounts'});

  if(!userId){
    const {data:created,error:createError}=await supabase.auth.admin.createUser({email,email_confirm:true,user_metadata:{title_prefix:titlePrefix,first_name:firstName,last_name:lastName,department},app_metadata:{role}});
    if(createError||!created.user)return reply(req,400,{error:createError?.message||'Could not create user'});
    userId=created.user.id;
    const {error:profileError}=await supabase.from('profiles').insert({id:userId,email,title_prefix:titlePrefix,first_name:firstName,last_name:lastName,department,role,active:true,default_program_id:defaultProgramId,limit_program_access:limitProgramAccess,created_by:caller.id});
    if(profileError){await supabase.auth.admin.deleteUser(userId);return reply(req,500,{error:`Could not create EduItqan profile: ${profileError.message}`});}
  }else{
    const {error:updateError}=await supabase.from('profiles').update({title_prefix:titlePrefix,first_name:firstName,last_name:lastName,department,role,active:true,default_program_id:defaultProgramId,limit_program_access:limitProgramAccess}).eq('id',userId);
    if(updateError)return reply(req,500,{error:`Could not update EduItqan profile: ${updateError.message}`});
    const {error:authUpdateError}=await supabase.auth.admin.updateUserById(userId,{user_metadata:{title_prefix:titlePrefix,first_name:firstName,last_name:lastName,department},app_metadata:{role}});
    if(authUpdateError)return reply(req,500,{error:'Could not update user authentication record'});
  }

  const {error:deleteError}=await supabase.from('program_memberships').delete().eq('user_id',userId);
  if(deleteError)return reply(req,500,{error:'Could not reset program access'});
  if(!isSupervisor&&accessibleProgramIds.length){
    const memberships=accessibleProgramIds.map((programId:string)=>({program_id:programId,user_id:userId,role,active:true,created_by:caller.id}));
    const {error:membershipError}=await supabase.from('program_memberships').insert(memberships);
    if(membershipError)return reply(req,500,{error:`Could not assign program access: ${membershipError.message}`});
  }

  await supabase.from('audit_log').insert({actor_id:caller.id,action:'create_or_assign_user',entity_type:'profile',entity_id:userId,details:{email,title_prefix:titlePrefix,role,department,scope:isSupervisor?'all_programs_read_only':'program_membership',limit_program_access:limitProgramAccess,program_ids:accessibleProgramIds}});
  return reply(req,200,{user:{id:userId,email,title_prefix:titlePrefix,first_name:firstName,last_name:lastName,department,role,scope:isSupervisor?'all_programs_read_only':'program_membership',limit_program_access:limitProgramAccess,program_ids:accessibleProgramIds,active:true}});
});