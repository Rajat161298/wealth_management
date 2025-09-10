import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

void main() {
  runApp(WealthSignalsApp());
}

class WealthSignalsApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Wealth Signals',
      theme: ThemeData.light().copyWith(
        primaryColor: Colors.deepOrange,
      ),
      home: SignalScreen(),
    );
  }
}

class Signal {
  String ticker;
  String action;
  String reason;
  String source;
  Signal({required this.ticker, required this.action, required this.reason, required this.source});
  factory Signal.fromJson(Map<String, dynamic> j) => Signal(
    ticker: j['ticker'] ?? '',
    action: j['action'] ?? 'WATCH',
    reason: j['reason'] ?? '',
    source: j['source'] ?? '',
  );
}

class SignalScreen extends StatefulWidget {
  @override
  _SignalScreenState createState() => _SignalScreenState();
}

class _SignalScreenState extends State<SignalScreen> {
  String filter = "All";
  bool loading = true;
  List<Signal> signals = [];
  String backendBase = "http://localhost:8000"; // change in Gitpod to preview URL if required

  @override
  void initState() {
    super.initState();
    fetchSignals();
  }

  Future<void> fetchSignals() async {
    setState(() { loading = true; });
    try {
      final resp = await http.get(Uri.parse("$backendBase/signals?limit=8")).timeout(Duration(seconds: 20));
      if (resp.statusCode == 200) {
        final List data = jsonDecode(resp.body);
        setState(() {
          signals = data.map((e) => Signal.fromJson(e)).toList();
        });
      } else {
        print("Backend error ${resp.statusCode}: ${resp.body}");
      }
    } catch (e) {
      print("Error fetching signals: $e");
    } finally {
      setState(() { loading = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    List<Signal> filtered = filter == "All" ? signals : signals.where((s) => s.action.toUpperCase() == filter.toUpperCase()).toList();
    return Scaffold(
      appBar: AppBar(
        title: Text("Wealth Signals"),
        actions: [
          IconButton(onPressed: fetchSignals, icon: Icon(Icons.refresh))
        ],
      ),
      body: Column(
        children: [
          Padding(
            padding: EdgeInsets.all(12),
            child: Wrap(
              spacing: 8,
              children: ["All", "BUY", "SELL", "WATCH"].map((f) {
                bool selected = filter == f;
                return ChoiceChip(
                  label: Text(f),
                  selected: selected,
                  onSelected: (v) {
                    setState(() { filter = f; });
                  },
                );
              }).toList(),
            ),
          ),
          if (loading) LinearProgressIndicator(),
          Expanded(
            child: RefreshIndicator(
              onRefresh: fetchSignals,
              child: ListView.builder(
                itemCount: filtered.length,
                itemBuilder: (context, idx) {
                  final s = filtered[idx];
                  final color = s.action.toUpperCase() == "BUY" ? Colors.green : s.action.toUpperCase() == "SELL" ? Colors.red : Colors.grey;
                  return Card(
                    margin: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    child: Padding(
                      padding: EdgeInsets.all(14),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Expanded(child: Text(s.ticker, style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18))),
                              Container(
                                padding: EdgeInsets.symmetric(vertical: 6, horizontal: 10),
                                decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(8)),
                                child: Text(s.action, style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                              )
                            ],
                          ),
                          SizedBox(height: 8),
                          Text(s.reason),
                          SizedBox(height: 8),
                          Text(s.source, style: TextStyle(fontStyle: FontStyle.italic, fontSize: 12)),
                          SizedBox(height: 10),
                          Row(mainAxisAlignment: MainAxisAlignment.end, children: [
                            ElevatedButton(onPressed: () {}, child: Text("Trade")),
                            SizedBox(width: 8),
                            OutlinedButton(onPressed: () {}, child: Text("Add to Watchlist"))
                          ])
                        ],
                      ),
                    ),
                  );
                },
              ),
            ),
          )
        ],
      ),
    );
  }
}
