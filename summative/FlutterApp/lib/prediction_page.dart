import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;

const String _apiUrl = 'https://student-grade-api.onrender.com/predict';

// ── Field descriptor ────────────────────────────────────────────────────────
class _FieldDef {
  final String key;
  final String label;
  final String hint;
  final int min;
  final int max;
  const _FieldDef(this.key, this.label, this.hint, this.min, this.max);
}

// ── All 30 input fields grouped by section ───────────────────────────────────
const _sections = <String, List<_FieldDef>>{
  'Personal Information': [
    _FieldDef('age',     'Age',                          '15 – 22',  15, 22),
    _FieldDef('sex',     'Sex  (0 = Female, 1 = Male)',  '0 or 1',    0,  1),
    _FieldDef('address', 'Address  (0 = Rural, 1 = Urban)', '0 or 1', 0, 1),
    _FieldDef('famsize', 'Family Size  (0 = ≤3, 1 = >3)', '0 or 1',  0,  1),
    _FieldDef('Pstatus', 'Parent Status  (0 = Apart, 1 = Together)', '0 or 1', 0, 1),
    _FieldDef('romantic','Romantic Relationship  (0 = No, 1 = Yes)', '0 or 1', 0, 1),
  ],
  'Family Background': [
    _FieldDef('Medu',    'Mother Education  (0 – 4)',    '0 – 4',  0, 4),
    _FieldDef('Fedu',    'Father Education  (0 – 4)',    '0 – 4',  0, 4),
    _FieldDef('Mjob',    'Mother Job  (0 – 4)',          '0 – 4',  0, 4),
    _FieldDef('Fjob',    'Father Job  (0 – 4)',          '0 – 4',  0, 4),
    _FieldDef('guardian','Guardian  (0=mother, 1=father, 2=other)', '0 – 2', 0, 2),
    _FieldDef('famrel',  'Family Relationship Quality  (1 – 5)', '1 – 5', 1, 5),
    _FieldDef('famsup',  'Family Educational Support  (0 = No, 1 = Yes)', '0 or 1', 0, 1),
  ],
  'School & Study': [
    _FieldDef('traveltime', 'Travel Time to School  (1 – 4)', '1 – 4', 1, 4),
    _FieldDef('studytime',  'Weekly Study Time  (1 – 4)',     '1 – 4', 1, 4),
    _FieldDef('failures',   'Past Class Failures  (0 – 4)',   '0 – 4', 0, 4),
    _FieldDef('schoolsup',  'Extra School Support  (0/1)',    '0 or 1', 0, 1),
    _FieldDef('paid',       'Extra Paid Classes  (0/1)',      '0 or 1', 0, 1),
    _FieldDef('activities', 'Extra-curricular Activities  (0/1)', '0 or 1', 0, 1),
    _FieldDef('nursery',    'Attended Nursery School  (0/1)', '0 or 1', 0, 1),
    _FieldDef('higher',     'Wants Higher Education  (0/1)',  '0 or 1', 0, 1),
    _FieldDef('internet',   'Internet Access at Home  (0/1)','0 or 1', 0, 1),
    _FieldDef('absences',   'Number of Absences  (0 – 93)',  '0 – 93', 0, 93),
  ],
  'Lifestyle': [
    _FieldDef('freetime', 'Free Time After School  (1 – 5)',    '1 – 5', 1, 5),
    _FieldDef('goout',    'Going Out with Friends  (1 – 5)',    '1 – 5', 1, 5),
    _FieldDef('Dalc',     'Workday Alcohol Consumption  (1 – 5)', '1 – 5', 1, 5),
    _FieldDef('Walc',     'Weekend Alcohol Consumption  (1 – 5)', '1 – 5', 1, 5),
    _FieldDef('health',   'Current Health Status  (1 – 5)',     '1 – 5', 1, 5),
  ],
  'Period Grades': [
    _FieldDef('G1', 'G1 – First Period Grade  (0 – 20)',  '0 – 20', 0, 20),
    _FieldDef('G2', 'G2 – Second Period Grade  (0 – 20)', '0 – 20', 0, 20),
  ],
};

// ── Page ─────────────────────────────────────────────────────────────────────
class PredictionPage extends StatefulWidget {
  const PredictionPage({super.key});

  @override
  State<PredictionPage> createState() => _PredictionPageState();
}

class _PredictionPageState extends State<PredictionPage> {
  final _formKey = GlobalKey<FormState>();
  bool   _loading = false;
  String _resultText  = 'Fill in all fields and tap Predict.';
  bool   _isSuccess   = false;
  bool   _hasResult   = false;

  // One controller per field key — built in initState to avoid lint warning
  final Map<String, TextEditingController> _controllers = {};

  @override
  void initState() {
    super.initState();
    for (final section in _sections.values) {
      for (final f in section) {
        _controllers[f.key] = TextEditingController();
      }
    }
  }

  @override
  void dispose() {
    for (final c in _controllers.values) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _predict() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() { _loading = true; });

    final body = <String, int>{};
    for (final section in _sections.values) {
      for (final f in section) {
        body[f.key] = int.parse(_controllers[f.key]!.text);
      }
    }

    try {
      final response = await http.post(
        Uri.parse(_apiUrl),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(body),
      ).timeout(const Duration(seconds: 30));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        setState(() {
          _isSuccess  = true;
          _hasResult  = true;
          _resultText = 'Predicted Final Grade (G3)\n${data["predicted_G3"]} / 20';
        });
      } else {
        String detail = response.body;
        try { detail = jsonDecode(response.body)['detail'] ?? detail; } catch (_) {}
        setState(() {
          _isSuccess  = false;
          _hasResult  = true;
          _resultText = 'Error ${response.statusCode}: $detail';
        });
      }
    } catch (e) {
      setState(() {
        _isSuccess  = false;
        _hasResult  = true;
        _resultText = 'Connection error:\n$e';
      });
    } finally {
      setState(() => _loading = false);
    }
  }

  // ── Single text field ───────────────────────────────────────────────────
  Widget _buildField(_FieldDef f) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: TextFormField(
        controller: _controllers[f.key],
        keyboardType: TextInputType.number,
        inputFormatters: [FilteringTextInputFormatter.digitsOnly],
        decoration: InputDecoration(
          labelText: f.label,
          hintText: f.hint,
          filled: true,
          fillColor: Colors.grey.shade50,
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
          contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        ),
        validator: (v) {
          if (v == null || v.isEmpty) return 'Required';
          final n = int.tryParse(v);
          if (n == null) return 'Must be a whole number';
          if (n < f.min || n > f.max) return 'Enter a value between ${f.min} and ${f.max}';
          return null;
        },
      ),
    );
  }

  // ── Section card ────────────────────────────────────────────────────────
  Widget _buildSection(String title, List<_FieldDef> fields) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              Container(width: 4, height: 18,
                  decoration: BoxDecoration(
                    color: const Color(0xFF1565C0),
                    borderRadius: BorderRadius.circular(2),
                  )),
              const SizedBox(width: 8),
              Text(title,
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.bold,
                    color: Color(0xFF1565C0),
                    letterSpacing: 0.4,
                  )),
            ]),
            const SizedBox(height: 10),
            ...fields.map(_buildField),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF0F4F8),
      appBar: AppBar(
        backgroundColor: const Color(0xFF1565C0),
        foregroundColor: Colors.white,
        elevation: 0,
        title: const Text('Student Grade Predictor',
            style: TextStyle(fontWeight: FontWeight.bold)),
        centerTitle: true,
      ),
      body: Column(
        children: [
          // ── Page header banner ─────────────────────────────────────────
          Container(
            width: double.infinity,
            color: const Color(0xFF1565C0),
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
            child: const Text(
              'Enter the student\'s details below to predict their\nfinal mathematics grade (G3) on a scale of 0 – 20.',
              style: TextStyle(color: Colors.white70, fontSize: 13, height: 1.5),
              textAlign: TextAlign.center,
            ),
          ),

          // ── Output display card (always visible) ───────────────────────
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 14, 16, 0),
            child: Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(vertical: 18, horizontal: 20),
              decoration: BoxDecoration(
                color: !_hasResult
                    ? Colors.white
                    : _isSuccess
                        ? const Color(0xFFE3F2FD)
                        : const Color(0xFFFFEBEE),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: !_hasResult
                      ? Colors.grey.shade300
                      : _isSuccess
                          ? const Color(0xFF1565C0)
                          : Colors.red.shade300,
                  width: 1.5,
                ),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.06),
                    blurRadius: 6,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              child: Row(
                children: [
                  Icon(
                    !_hasResult
                        ? Icons.info_outline
                        : _isSuccess
                            ? Icons.check_circle_outline
                            : Icons.error_outline,
                    color: !_hasResult
                        ? Colors.grey
                        : _isSuccess
                            ? const Color(0xFF1565C0)
                            : Colors.red,
                    size: 28,
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      _resultText,
                      style: TextStyle(
                        fontSize: _isSuccess && _hasResult ? 18 : 14,
                        fontWeight: _isSuccess && _hasResult
                            ? FontWeight.bold
                            : FontWeight.normal,
                        color: !_hasResult
                            ? Colors.grey.shade600
                            : _isSuccess
                                ? const Color(0xFF1565C0)
                                : Colors.red.shade700,
                        height: 1.4,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),

          const SizedBox(height: 10),

          // ── Scrollable form ────────────────────────────────────────────
          Expanded(
            child: Form(
              key: _formKey,
              child: ListView(
                padding: const EdgeInsets.fromLTRB(16, 4, 16, 16),
                children: [
                  ..._sections.entries.map(
                    (e) => _buildSection(e.key, e.value),
                  ),

                  // ── Predict button ─────────────────────────────────────
                  const SizedBox(height: 4),
                  SizedBox(
                    height: 52,
                    child: ElevatedButton(
                      onPressed: _loading ? null : _predict,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF1565C0),
                        foregroundColor: Colors.white,
                        disabledBackgroundColor: Colors.blueGrey.shade200,
                        shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(10)),
                        textStyle: const TextStyle(
                            fontSize: 16, fontWeight: FontWeight.bold),
                      ),
                      child: _loading
                          ? const SizedBox(
                              height: 22,
                              width: 22,
                              child: CircularProgressIndicator(
                                  color: Colors.white, strokeWidth: 2.5),
                            )
                          : const Text('Predict'),
                    ),
                  ),
                  const SizedBox(height: 24),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
