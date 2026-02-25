import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
// ignore: avoid_web_libraries_in_flutter
import 'dart:html' as html;
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

void main() {
  runApp(const RaagApp());
}

class RaagApp extends StatelessWidget {
  const RaagApp({super.key});

  @override
  Widget build(BuildContext context) {
    return const MaterialApp(
      debugShowCheckedModeBanner: false,
      home: RaagRecorderPage(),
    );
  }
}

class RaagRecorderPage extends StatefulWidget {
  const RaagRecorderPage({super.key});

  @override
  State<RaagRecorderPage> createState() => _RaagRecorderPageState();
}

class _RaagRecorderPageState extends State<RaagRecorderPage> {
  html.MediaRecorder? recorder;
  html.MediaStream? mediaStream;
  List<html.Blob> audioChunks = [];
  Uint8List? recordedAudio;
  bool isRecording = false;
  String result = "No prediction yet";

  // 🔁 Replace with your deployed API endpoint
  final String apiUrl = "http://localhost:8000/predict";

  Future<void> startRecording() async {
    // request microphone access and keep stream reference for later stopping
    final stream = await html.window.navigator.mediaDevices?.getUserMedia({
      'audio': true,
    });
    if (stream == null) return;

    mediaStream = stream;
    recorder = html.MediaRecorder(stream);
    audioChunks.clear();

    // collect audio chunks as they become available
    recorder!.addEventListener('dataavailable', (event) {
      final blobEvent = event as html.BlobEvent;
      audioChunks.add(blobEvent.data!);
    });

    recorder!.addEventListener('stop', (event) async {
      // convert collected blobs into bytes and store
      final blob = html.Blob(audioChunks, 'audio/wav');
      final reader = html.FileReader();
      reader.readAsArrayBuffer(blob);
      await reader.onLoad.first;
      recordedAudio = reader.result as Uint8List;
      updatePrediction(); // automatically send once we have data
    });

    recorder!.start();

    setState(() {
      isRecording = true;
      result = "Recording...";
    });
  }

  Future<void> stopRecording() async {
    recorder?.stop();
    // stop the microphone tracks too
    mediaStream?.getTracks().forEach((track) => track.stop());

    setState(() {
      isRecording = false;
    });
  }

  // helper to send raw bytes to the prediction API and return decoded map
  Future<Map<String, dynamic>> sendAudioBytes(Uint8List bytes) async {
    try {
      final request = http.MultipartRequest('POST', Uri.parse(apiUrl));
      request.files.add(
        http.MultipartFile.fromBytes('file', bytes, filename: 'recording.wav'),
      );

      final response = await request.send();
      final responseBody = await response.stream.bytesToString();
      if (response.statusCode == 200 && responseBody.isNotEmpty) {
        return jsonDecode(responseBody) as Map<String, dynamic>;
      }
    } catch (_) {}
    return {};
  }

  // called after recording finishes or when the user requests
  Future<void> updatePrediction() async {
    if (recordedAudio == null) return;

    setState(() {
      result = "Predicting...";
    });

    final response = await sendAudioBytes(recordedAudio!);

    if (response.isNotEmpty && response.containsKey('raag')) {
      final raag = response['raag'];
      final confidence = (response['confidence'] * 100).toStringAsFixed(1);
      setState(() {
        result = "Raag: $raag | Confidence: $confidence%";
      });
    } else {
      setState(() {
        result = "Connection failed";
      });
    }
  }

  void reset() {
    audioChunks.clear();
    result = "No prediction yet";
    setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Raag Recognition")),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              "Microphone Recorder",
              style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 20),

            Text(isRecording ? "Recording..." : "Idle"),

            const SizedBox(height: 30),

            const Text(
              "Prediction",
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 10),
            Text(result, style: const TextStyle(fontSize: 18)),

            const SizedBox(height: 40),

            Row(
              children: [
                ElevatedButton(
                  onPressed: isRecording ? null : startRecording,
                  child: const Text("Start Recording"),
                ),
                const SizedBox(width: 10),
                ElevatedButton(
                  onPressed: isRecording ? stopRecording : null,
                  child: const Text("Stop & Predict"),
                ),
                const SizedBox(width: 10),
                ElevatedButton(onPressed: reset, child: const Text("Reset")),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
