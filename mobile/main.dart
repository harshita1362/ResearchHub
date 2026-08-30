import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'config.dart';

void main() => runApp(const ResearchHubApp());

class ResearchHubApp extends StatelessWidget {
  const ResearchHubApp({super.key});
  @override
  Widget build(BuildContext context) => MaterialApp(
    debugShowCheckedModeBanner: false,
    title: 'ResearchHub',
    theme: ThemeData(colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xff244d43)), useMaterial3: true),
    home: const LoginPage(),
  );
}

class Api {
  static Future<Map<String,dynamic>> post(String path, Map<String,dynamic> body) async {
    final r=await http.post(Uri.parse('$apiBaseUrl$path'),headers:{'Content-Type':'application/json'},body:jsonEncode(body));
    final d=jsonDecode(r.body);
    if(r.statusCode>=400) throw Exception(d['detail']??'Request failed');
    return Map<String,dynamic>.from(d);
  }
  static Future<List<dynamic>> get(String path) async {
    final p=await SharedPreferences.getInstance();
    final token=p.getString('token')??'';
    final r=await http.get(Uri.parse('$apiBaseUrl$path'),headers:{'Authorization':'Bearer $token'});
    final d=jsonDecode(r.body);
    if(r.statusCode>=400) throw Exception(d['detail']??'Request failed');
    return List<dynamic>.from(d);
  }
}

class LoginPage extends StatefulWidget {const LoginPage({super.key}); @override State<LoginPage> createState()=>_LoginPageState();}
class _LoginPageState extends State<LoginPage>{
 final email=TextEditingController(),password=TextEditingController();
 bool register=false,loading=false;
 Future<void> submit() async{
  setState(()=>loading=true);
  try{
   final d=await Api.post(register?'/api/auth/register':'/api/auth/login',{'email':email.text,'password':password.text,...(register?{'name':'Mobile Researcher'}:{})});
   final p=await SharedPreferences.getInstance();await p.setString('token',d['token']);await p.setString('name',d['user']['name']);
   if(mounted)Navigator.pushReplacement(context,MaterialPageRoute(builder:(_)=>const HomePage()));
  }catch(e){if(mounted)ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text(e.toString())));}
  setState(()=>loading=false);
 }
 @override Widget build(BuildContext c)=>Scaffold(body:Center(child:SingleChildScrollView(padding:const EdgeInsets.all(28),child:Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:[
 const Text('🔬 ResearchHub',style:TextStyle(fontSize:28,fontWeight:FontWeight.bold)),const SizedBox(height:10),
 Text(register?'Create your research profile':'Welcome back',style:const TextStyle(fontSize:24,fontWeight:FontWeight.w600)),
 const SizedBox(height:28),TextField(controller:email,decoration:const InputDecoration(labelText:'Email',border:OutlineInputBorder())),const SizedBox(height:12),
 TextField(controller:password,obscureText:true,decoration:const InputDecoration(labelText:'Password',border:OutlineInputBorder())),const SizedBox(height:18),
 FilledButton(onPressed:loading?null:submit,child:Text(loading?'Please wait...':register?'Create account':'Sign in')),
 TextButton(onPressed:()=>setState(()=>register=!register),child:Text(register?'Already have an account? Sign in':'New here? Create account'))
 ])));
}

class HomePage extends StatefulWidget {const HomePage({super.key}); @override State<HomePage> createState()=>_HomePageState();}
class _HomePageState extends State<HomePage>{
 List<dynamic> services=[];
 @override void initState(){super.initState();Api.get('/api/services').then((x)=>setState(()=>services=x)).catch((_){});}
 @override Widget build(BuildContext c)=>Scaffold(appBar:AppBar(title:const Text('ResearchHub'),actions:[IconButton(onPressed:()=>Navigator.push(context,MaterialPageRoute(builder:(_)=>const ProjectsPage())),icon:const Icon(Icons.dashboard_outlined))]),body:ListView(padding:const EdgeInsets.all(18),children:[
 const Text('Research, reimagined.',style:TextStyle(fontSize:32,fontWeight:FontWeight.bold)),const SizedBox(height:8),
 const Text('Find support, manage projects and accelerate your research.'),const SizedBox(height:25),
 const Text('Research Services',style:TextStyle(fontSize:21,fontWeight:FontWeight.bold)),
 ...services.map((s)=>Card(child:ListTile(leading:Text(s['icon']??'🔬',style:const TextStyle(fontSize:25)),title:Text(s['title']),subtitle:Text('₹${s['price_inr']} • ${s['duration']}'),trailing:const Icon(Icons.arrow_forward_ios,size:16))))
 ]));
}

class ProjectsPage extends StatefulWidget {const ProjectsPage({super.key}); @override State<ProjectsPage> createState()=>_ProjectsPageState();}
class _ProjectsPageState extends State<ProjectsPage>{
 List<dynamic> projects=[];
 @override void initState(){super.initState();load();}
 Future<void> load()async{try{setState(()=>projects=await Api.get('/api/projects'));}catch(_){}}
 @override Widget build(BuildContext c)=>Scaffold(appBar:AppBar(title:const Text('My Research')),body:ListView(padding:const EdgeInsets.all(18),children:projects.map((p)=>Card(child:ListTile(title:Text(p['title']),subtitle:Text('${p['status']} • ${p['progress']}% complete'),onTap:(){}))).toList()));
}
