window.EDUITQAN_SEED = {
    role:'Head of Department',
    program:{institution:'Example University',college:'College of Applied Health Sciences',department:'Health Information Management',name:'Bachelor of Health Information Management',programType:'Bachelor',academicYear:'2026–2027'},
    academicYears:['2026–2027','2025–2026'],
    plos:[
      {code:'K1',name:'Explain foundational concepts and principles in health information management.',target:70},
      {code:'K2',name:'Interpret health data standards, classifications and information governance requirements.',target:70},
      {code:'S1',name:'Apply health information methods to analyze and improve healthcare processes.',target:70},
      {code:'S2',name:'Use digital health tools and data to support evidence-informed decisions.',target:70},
      {code:'V1',name:'Demonstrate professional, ethical and responsible practice.',target:70},
      {code:'V2',name:'Collaborate effectively and communicate within multidisciplinary healthcare settings.',target:70}
    ],
    reports:[],
    operational:[],
    automations:[
      {id:'a1',icon:'→',name:'Instructor submission → Quality approval queue',description:'Submitting a Course Report locks instructor editing and places the exact report in the Coordinator review queue.',on:true},
      {id:'a2',icon:'✓',name:'Quality approval → official CLO results',description:'Only Coordinator-approved CLO results are released to PLO calculations and the HOD dashboard.',on:true},
      {id:'a3',icon:'◎',name:'Approved CLO → semester PLO',description:'For All-section reports, Combined is recalculated and verified first; approved CLOs are then aggregated separately for S1, S2, and Summer, weighted by completed students.',on:true},
      {id:'a4',icon:'◫',name:'Semester PLOs → Annual Program Report',description:'The APR combines approved S1, S2, and Summer results for the selected academic year with drill-down traceability.',on:true},
      {id:'a5',icon:'▣',name:'Structured report data → Course Portfolio',description:'Course Portfolio files are generated on demand from EduItqan data plus session-only document selections. Selected files are never stored by EduItqan.',on:true}
    ],
    audit:[]
  };
