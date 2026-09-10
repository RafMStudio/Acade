import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "npm:@supabase/supabase-js@2";

const cors = {
  "Access-Control-Allow-Origin": "https://acadeloop.com",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};
const reply = (status:number, body:unknown) => new Response(JSON.stringify(body), { status, headers:{...cors,"Content-Type":"application/json","Cache-Control":"no-store"} });
const allowedPrefixes = ['Mr.','Mrs.','Dr.'];

Deno.serve(async (req:Request) => {
  if(req.method === "OPTIONS") return new Response("ok", {headers:cors});
  if(req.method !== "POST") return reply(405,{error:"Method not allowed"});
  const token=(req.headers.get("Authorization")||"").replace(/^Bearer\s+/i,"").trim();
  if(!token) return reply(401,{error:"Authentication required"});
  const supabase=createClient(Deno.env.get("SUPABASE_URL")!,Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,{auth:{persistSession:false}});
  const {data:authData,error:authError}=await supabase.auth.getUser(token);
  if(authError||!authData.user) return reply(401,{error:"Invalid session"});
  const {data:caller}=await supabase.from("profiles").select("id,role,active").eq("id",authData.user.id).single();
  if(!caller?.active||!['SystemAdmin','HOD'].includes(caller.role)) return reply(403,{error:"You cannot add users"});

  let body:any; try{body=await req.json()}catch{return reply(400,{error:"Invalid request"})}
  const email=String(body.email||"").trim().toLowerCase();
  const titlePrefix=String(body.title_prefix||body.titlePrefix||"").trim();
  const firstName=String(body.first_name||body.firstName||"").trim();
  const lastName=String(body.last_name||body.lastName||"").trim();
  const department=String(body.department||"").trim();
  const role=String(body.role||"").trim();
  const programId=String(body.program_id||body.programId||"").trim()||null;
  if(!email||!/^\S+@\S+\.\S+$/.test(email)) return reply(400,{error:"A valid email is required"});
  if(!allowedPrefixes.includes(titlePrefix)) return reply(400,{error:"Prefix must be Mr., Mrs., or Dr."});
  if(!firstName||!lastName) return reply(400,{error:"First and last name are required"});
  if(!['HOD','Coordinator','Instructor'].includes(role)) return reply(400,{error:"Role must be HOD, Coordinator, or Instructor"});
  if(caller.role==='HOD'&&role==='HOD') return reply(403,{error:"Only System Administrator can appoint an HOD"});
  if(!programId) return reply(400,{error:"An academic program is required"});

  const {data:program}=await supabase.from("academic_programs").select("id,status,department").eq("id",programId).maybeSingle();
  if(!program) return reply(404,{error:"Academic program not found"});
  if(caller.role==='HOD'){
    const {data:membership}=await supabase.from("program_memberships").select("id").eq("program_id",programId).eq("user_id",caller.id).eq("role","HOD").eq("active",true).maybeSingle();
    if(!membership) return reply(403,{error:"You may only add users to a program you head"});
  }

  const {data:existingProfile}=await supabase.from("profiles").select("id,email").eq("email",email).maybeSingle();
  let userId=existingProfile?.id||null;
  if(!userId){
    const {data:created,error:createError}=await supabase.auth.admin.createUser({email,email_confirm:true,user_metadata:{title_prefix:titlePrefix,first_name:firstName,last_name:lastName,department},app_metadata:{role}});
    if(createError||!created.user) return reply(400,{error:createError?.message||"Could not create user"});
    userId=created.user.id;
    const {error:profileError}=await supabase.from("profiles").insert({id:userId,email,title_prefix:titlePrefix,first_name:firstName,last_name:lastName,department:department||program.department||'',role,active:true,default_program_id:programId,created_by:caller.id});
    if(profileError){await supabase.auth.admin.deleteUser(userId);return reply(500,{error:profileError.message});}
  }else{
    const {error:updateError}=await supabase.from("profiles").update({title_prefix:titlePrefix,first_name:firstName,last_name:lastName,department:department||program.department||'',role,active:true,default_program_id:programId}).eq("id",userId);
    if(updateError) return reply(500,{error:updateError.message});
    await supabase.auth.admin.updateUserById(userId,{user_metadata:{title_prefix:titlePrefix,first_name:firstName,last_name:lastName,department},app_metadata:{role}});
  }

  const {error:membershipError}=await supabase.from("program_memberships").upsert({program_id:programId,user_id:userId,role,active:true,created_by:caller.id},{onConflict:"program_id,user_id"});
  if(membershipError) return reply(500,{error:membershipError.message});
  await supabase.from("audit_log").insert({actor_id:caller.id,action:"create_or_assign_user",entity_type:"profile",entity_id:userId,details:{email,title_prefix:titlePrefix,role,program_id:programId}});
  return reply(200,{user:{id:userId,email,title_prefix:titlePrefix,first_name:firstName,last_name:lastName,department:department||program.department||'',role,program_id:programId,active:true}});
});
