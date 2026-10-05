const express = require('express');
const cors = require('cors');
const bcrypt = require('bcrypt');
const nodemailer = require('nodemailer');
const rateLimit = require('express-rate-limit');
const db = require('./database');
const multer = require('multer');
const { GoogleGenAI } = require('@google/genai');
const fsModule = require('fs');
const path = require('path');
require('dotenv').config();

const upload = multer({ dest: 'uploads/' });

// Initialize Gemini Client
const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });


const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors({
  origin: true, // Allow requests from any frontend port (5173, 5174, etc.)
  credentials: true
}));
app.use(express.json());

function getPythonExecutable() {
  const venvPath = path.resolve(path.join(__dirname, '..', '.venv', 'Scripts', 'python.exe'));
  if (fsModule.existsSync(venvPath)) {
    return venvPath;
  }
  return 'python';
}

// Silent handler for Chrome DevTools probes
app.use('/.well-known', (req, res) => res.status(200).json({ status: 'ok' }));

// Root health check route
app.get('/', (req, res) => res.json({ status: 'ok', message: 'Anuvad (SignBridge) Backend API Server is Running' }));


const forgotPasswordLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, 
  max: 3, 
  message: { error: 'Too many password reset attempts, please try again after 15 minutes' }
});



const transporter = nodemailer.createTransport({
  host: 'smtp.gmail.com',
  port: 465,
  secure: true, // use SSL
  auth: {
    user: process.env.EMAIL_USER || '15shreyashetty@gmail.com',
    pass: process.env.EMAIL_PASS || 'vrvl delv pozp pnqo'
  }
});


const generateOTP = () => {
  return Math.floor(100000 + Math.random() * 900000).toString();
};


app.post('/api/auth/register', async (req, res) => {
  const { fullName, email, password } = req.body;
  if (!fullName || !email || !password) return res.status(400).json({ error: 'Full name, email and password are required' });

  try {
    const hashedPassword = await bcrypt.hash(password, 10);
    db.run('INSERT INTO users (email, password, full_name) VALUES (?, ?, ?)', [email, hashedPassword, fullName], function(err) {
      if (err) {
        if (err.message.includes('UNIQUE')) {
          return res.status(400).json({ error: 'User already exists.' });
        }
        return res.status(500).json({ error: 'Database error during registration.' });
      }
      res.json({ message: 'Registration successful', email });
    });
  } catch (error) {
    res.status(500).json({ error: 'Server error' });
  }
});


app.post('/api/auth/login', (req, res) => {
  console.log('\n[LOGIN] Request received.');
  const { email, password } = req.body;
  console.log(`[LOGIN] Email received: ${email}`);

  if (!email || !password) {
    console.log('[LOGIN] Failure: Email and password are required');
    return res.status(400).json({ error: 'Email and password are required' });
  }

  db.get('SELECT * FROM users WHERE email = ?', [email], async (err, user) => {
    if (err) {
      console.error('[LOGIN] Failure: Database error:', err);
      return res.status(500).json({ error: 'Database error' });
    }
    
    if (!user) {
      console.log(`[LOGIN] Failure: User NOT found in database for email: ${email}`);
      return res.status(401).json({ error: 'Invalid email or password.' });
    }
    
    console.log(`[LOGIN] User found in database: ID=${user.id}, FullName=${user.full_name}`);
    
    const match = await bcrypt.compare(password, user.password);
    console.log(`[LOGIN] Password hash comparison result: ${match}`);
    
    if (match) {
      console.log(`[LOGIN] Success: Login successful for ${email}`);
      res.json({ message: 'Login successful', email, fullName: user.full_name });
    } else {
      console.log(`[LOGIN] Failure: Incorrect password for ${email}`);
      res.status(401).json({ error: 'Invalid email or password.' });
    }
  });
});


app.post('/api/auth/forgot-password', forgotPasswordLimiter, (req, res) => {
  console.log(`\n[FORGOT PASSWORD] Request received for password reset.`);
  const { email } = req.body;
  console.log(`[FORGOT PASSWORD] Email extracted from payload: ${email}`);

  if (!email || !/^\\S+@\\S+\\.\\S+$/.test(email)) {
    return res.status(400).json({ error: 'Please enter a valid email address.' });
  }

  db.get('SELECT * FROM users WHERE email = ?', [email], (err, user) => {
    if (err) {
      console.error(`[FORGOT PASSWORD] Database error:`, err);
      return res.status(500).json({ error: 'Database error' });
    }
    if (!user) {
      console.log(`[FORGOT PASSWORD] User NOT found in database for email: ${email}`);
      return res.status(404).json({ error: 'No account was found with this email address.' });
    }
    
    console.log(`[FORGOT PASSWORD] User found in database: ${user.full_name}`);

    const otp = generateOTP();
    console.log(`[FORGOT PASSWORD] OTP generated.`);
    const expiresAt = Date.now() + 10 * 60 * 1000; // 10 minutes

    db.run('INSERT INTO password_resets (email, otp, expires_at) VALUES (?, ?, ?)', [email, otp, expiresAt], (err) => {
      if (err) {
        console.error(`[FORGOT PASSWORD] Database error saving OTP:`, err);
        return res.status(500).json({ error: 'Database error' });
      }
      console.log(`[FORGOT PASSWORD] OTP saved to database successfully.`);

      const userFirstName = user.full_name ? user.full_name.split(' ')[0] : 'User';
      const senderEmail = process.env.EMAIL_USER || '15shreyashetty@gmail.com';

      const mailOptions = {
        from: `"SignBridge" <${senderEmail}>`,
        to: email,
        subject: 'SignBridge Password Reset OTP',
        text: `Hello, ${userFirstName},\n\nYou requested a password reset for your SignBridge account. Your 6-digit OTP is: ${otp}\n\nThis OTP will expire in 10 minutes. If you did not request this, please ignore this email.\n\nBest regards,\nThe SignBridge Team`,
        html: `
          <div style="font-family: Arial, sans-serif; color: #333; line-height: 1.6; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 8px;">
            <h2 style="color: #6a1b9a;">SignBridge Password Reset</h2>
            <p>Hello, <strong>${userFirstName}</strong>,</p>
            <p>We received a request to reset the password for your SignBridge account. Please use the following One-Time Password (OTP) to proceed:</p>
            <div style="text-align: center; margin: 30px 0;">
              <span style="font-size: 32px; font-weight: bold; letter-spacing: 4px; color: #333; background: #f4f4f4; padding: 15px 30px; border-radius: 8px; border: 1px dashed #ccc;">${otp}</span>
            </div>
            <p>This OTP is valid for <strong>10 minutes</strong>. If you did not request a password reset, please ignore this email or contact support if you have concerns.</p>
            <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;" />
            <p style="font-size: 14px; color: #777;">Best regards,<br/><strong>The SignBridge Team</strong></p>
          </div>
        `
      };

      console.log(`[FORGOT PASSWORD] Email send started to ${email} via ${senderEmail}...`);

      transporter.sendMail(mailOptions, (error, info) => {
        if (error) {
          console.error(`[FORGOT PASSWORD] Email send FAILED! Error:`, error);
          return res.status(500).json({ error: 'Unable to send OTP at the moment. Please try again later.' });
        }
        console.log(`[FORGOT PASSWORD] Email send SUCCEEDED! Message ID: ${info.messageId}`);
        console.log(`[FORGOT PASSWORD] SMTP Server Response: ${info.response}`);
        res.json({ message: 'OTP sent successfully. Please check your email.' });
      });
    });
  });
});


app.post('/api/auth/verify-otp', (req, res) => {
  const { email, otp } = req.body;
  if (!email || !otp) return res.status(400).json({ error: 'Email and OTP are required' });

  const now = Date.now();
  db.get('SELECT * FROM password_resets WHERE email = ? ORDER BY id DESC LIMIT 1', [email], (err, record) => {
    if (err) return res.status(500).json({ error: 'Database error' });
    if (!record) return res.status(400).json({ error: 'Invalid or expired OTP.' });

    if (record.otp !== otp || record.expires_at < now) {
      return res.status(400).json({ error: 'Invalid or expired OTP.' });
    }

    res.json({ message: 'OTP verified successfully.' });
  });
});


app.post('/api/auth/reset-password', (req, res) => {
  const { email, otp, newPassword } = req.body;
  if (!email || !otp || !newPassword) return res.status(400).json({ error: 'Missing required fields' });

  const now = Date.now();
  db.get('SELECT * FROM password_resets WHERE email = ? ORDER BY id DESC LIMIT 1', [email], async (err, record) => {
    if (err) return res.status(500).json({ error: 'Database error' });
    if (!record || record.otp !== otp || record.expires_at < now) {
      return res.status(400).json({ error: 'Invalid or expired OTP.' });
    }

    try {
      const hashedPassword = await bcrypt.hash(newPassword, 10);
      db.run('UPDATE users SET password = ? WHERE email = ?', [hashedPassword, email], function(err) {
        if (err) return res.status(500).json({ error: 'Database error' });
        
        db.run('DELETE FROM password_resets WHERE id = ?', [record.id]);
        res.json({ message: 'Password updated successfully.' });
      });
    } catch (error) {
      res.status(500).json({ error: 'Server error' });
    }
  });
});


app.post('/api/predict_video', upload.single('video'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'No video file provided' });
    }

    const originalFilePath = path.resolve(req.file.path);
    // Add .mp4 extension so OpenCV can read it properly
    const filePath = originalFilePath + '.mp4';
    try { fsModule.renameSync(originalFilePath, filePath); } catch(e) {}
    
    console.log('[GEMINI] Received video file:', req.file.originalname);
    console.log('[GEMINI] Extracting frames to bypass Video API 503 error...');
    
    const { exec } = require('child_process');
    const pythonExecutable = getPythonExecutable();
    const extractScriptPath = path.resolve(path.join(__dirname, '..', 'pipeline', 'extract_frames.py'));
    
    exec(`"${pythonExecutable}" "${extractScriptPath}" "${filePath}"`, { maxBuffer: 1024 * 1024 * 50 }, async (error, stdout, stderr) => {

      if (error) {
        console.error('[GEMINI] Error extracting frames:', error);
        return res.status(500).json({ error: 'Failed to extract frames' });
      }

      try {
        const frameData = JSON.parse(stdout);
        if (frameData.error) throw new Error(frameData.error);
        
        const contents = [
          `You are an expert Indian Sign Language (ISL) translator analyzing video frames.
CRITICAL INSTRUCTIONS:
1. SUBTITLE CHECK: First, check if there are SUBTITLES, CAPTIONS, or TEXT overlays on screen in the video frames. If subtitles are present, read the text from the subtitles accurately.
2. HAND GESTURE CHECK: If no subtitles are present, analyze the physical hand shapes, finger configurations, arm motion, and gesture transitions step-by-step to identify the sign.
3. Return your response ONLY as a valid JSON object with exactly three keys: "reasoning", "raw_gestures", and "nlp_sentence".
4. "reasoning": Describe the subtitles found or hand motions observed.
5. "raw_gestures": The main sign word, phrase, or label detected.
6. "nlp_sentence": The complete, grammatically correct English translation.
7. Do not output any markdown code blocks or extra text, only the raw JSON object.`
        ];
        
        for (const b64 of frameData.frames) {
          contents.push({ inlineData: { data: b64, mimeType: "image/jpeg" } });
        }
        
        console.log('[GEMINI] Sending frames for lightning-fast prediction...');
        let response;
        let retries = 2; // Fail fast
        let delay = 1000;
        let geminiSuccess = false;
        
        while (retries > 0) {
          try {
            response = await ai.models.generateContent({
              model: 'gemini-3.8-flash',
              contents: contents
            });
            geminiSuccess = true;
            break; // Success
          } catch (err) {
            if (err.status === 429 || (err.message && err.message.includes('429'))) {
              console.log(`[GEMINI] 429 Rate Limit hit. Failing over immediately to save time.`);
              break; 
            }
            else if ((err.status === 503 || (err.message && err.message.includes('503'))) && retries > 1) {
              console.log(`[GEMINI] 503 High Demand hit. Retrying in ${delay}ms... (${retries - 1} retries left)`);
              await new Promise((resolve) => setTimeout(resolve, delay));
              retries--;
              delay *= 2; 
            } else {
              console.error('[GEMINI] API completely failed or exhausted retries.');
              break;
            }
          }
        }
        
        if (geminiSuccess && response) {
          let translationText = response.text.trim();
          translationText = translationText.replace(/^```json\s*/, '').replace(/\s*```$/, '');
          
          let parsedResult;
          try {
            parsedResult = JSON.parse(translationText);
          } catch (e) {
            parsedResult = { reasoning: "Failed to parse JSON.", raw_gestures: translationText, nlp_sentence: translationText };
          }
          
          console.log('[GEMINI] Reasoning:', parsedResult.reasoning);
          console.log('[GEMINI] Raw Gestures:', parsedResult.raw_gestures);
          console.log('[GEMINI] NLP Sentence:', parsedResult.nlp_sentence);

          // Auto-learn landmarks from subtitled video in background
          const signLabel = (parsedResult.raw_gestures || parsedResult.nlp_sentence || "").split(',')[0].trim();
          if (signLabel && signLabel.length < 30) {
            console.log(`[AUTO-LEARN] Extracting MediaPipe landmarks from video for sign: '${signLabel}'...`);
            const learnScriptPath = path.resolve(path.join(__dirname, '..', 'pipeline', 'learn_from_video.py'));
            exec(`"${pythonExecutable}" "${learnScriptPath}" "${filePath}" "${signLabel.replace(/"/g, '')}"`, (err, stdout, stderr) => {
              try { fsModule.unlinkSync(filePath); } catch (e) {}
              if (stdout) console.log('[AUTO-LEARN Output]:', stdout);
            });
          } else {
            try { fsModule.unlinkSync(filePath); } catch (e) {}
          }

          return res.json({ success: true, translation: parsedResult.nlp_sentence, raw: parsedResult.raw_gestures, source: 'Gemini AI' });
        } else {
          throw new Error("Gemini API Unavailable");
        }
        
      } catch (err) {
        const { execFile } = require('child_process');
        console.log('[SUBTITLE READER] Checking video for subtitles/captions...');
        const subtitleScriptPath = path.resolve(path.join(__dirname, '..', 'pipeline', 'read_subtitle.py'));
        const originalName = (req.file && req.file.originalname) ? req.file.originalname : "";
        
        execFile(pythonExecutable, [subtitleScriptPath, filePath, originalName], async (subErr, subStdout) => {
          const subText = (subStdout || "").trim();
          
          if (subText && subText !== "NO_SUBTITLE_FOUND" && subText !== "UNCERTAIN") {
            console.log('[SUBTITLE READER] Subtitle text extracted:', subText);
            
            // Auto-learn landmarks from subtitled video in background
            const learnScriptPath = path.resolve(path.join(__dirname, '..', 'pipeline', 'learn_from_video.py'));
            execFile(pythonExecutable, [learnScriptPath, filePath, subText], (e, out) => {
              try { fsModule.unlinkSync(filePath); } catch (e) {}
              if (out) console.log('[AUTO-LEARN Output]:', out);
            });
            
            return res.json({ success: true, translation: subText, raw: subText, source: 'Subtitle Reader' });
          }

          // If no subtitles, process video hand landmarks using Local AI Model
          console.log('[LOCAL LANDMARK AI] Processing video hand landmarks locally...');
          const lstmScriptPath = path.resolve(path.join(__dirname, '..', 'pipeline', 'process_video_lstm.py'));
          
          execFile(pythonExecutable, [lstmScriptPath, filePath], { cwd: path.resolve(path.join(__dirname, '..')) }, (error, stdout, stderr) => {
            try { fsModule.unlinkSync(filePath); } catch (e) {} // Clean up video
      
            if (error) {
              console.error('[LOCAL LANDMARK AI] Error:', error);
              return res.status(500).json({ error: 'Failed to translate video.' });
            }
      
            const lines = stdout.trim().split(/\r?\n/).map(l => l.trim()).filter(l => l && !l.includes('WARNING') && !l.includes('tensorflow') && !l.includes('oneDNN') && !l.includes('deprecated'));
            const rawTranslation = lines.pop() || "UNCERTAIN";
            console.log('[LOCAL LANDMARK AI] Raw Sign Detected:', rawTranslation);
            
            const nlpScriptPath = path.resolve(path.join(__dirname, '..', 'pipeline', 'nlp_formatter.py'));
            execFile(pythonExecutable, [nlpScriptPath, rawTranslation], (nlpErr, nlpStdout) => {
              let nlpSentence = (nlpStdout || "").trim();
              if (!nlpSentence) {
                nlpSentence = rawTranslation.replace(/^\d+\.\s*/, '').replace(/_/g, ' ');
                nlpSentence = nlpSentence.charAt(0).toUpperCase() + nlpSentence.slice(1).toLowerCase() + ".";
              }
              console.log('[LOCAL NLP LAYER] Formatted output:', nlpSentence);
              res.json({ success: true, translation: nlpSentence, raw: rawTranslation, source: 'Local AI (Landmark Matching)' });
            });
          });
        });
        // --- END SUBTITLE & LOCAL FALLBACK PIPELINE ---
      }
    });

  } catch (error) {
    console.error('[SERVER] Error during setup:', error);
    res.status(500).json({ error: 'Server error: ' + (error.message || 'Unknown error') });
  }
});

app.post('/api/learn_video', upload.single('video'), async (req, res) => {
  try {
    if (!req.file) return res.status(400).json({ error: 'No video file provided' });
    const label = req.body.label;
    if (!label) return res.status(400).json({ error: 'No sign label provided' });

    const originalFilePath = path.resolve(req.file.path);
    const filePath = originalFilePath + '.mp4';
    try { fsModule.renameSync(originalFilePath, filePath); } catch(e) {}

    const { exec } = require('child_process');
    const pythonExecutable = getPythonExecutable();
    const learnScriptPath = path.resolve(path.join(__dirname, '..', 'pipeline', 'learn_from_video.py'));

    console.log(`[AUTO-LEARN] Manual training request received for label: '${label}'`);
    exec(`"${pythonExecutable}" "${learnScriptPath}" "${filePath}" "${label.replace(/"/g, '')}"`, (error, stdout, stderr) => {
      try { fsModule.unlinkSync(filePath); } catch (e) {}
      if (error) {
        console.error('[AUTO-LEARN] Error:', error);
        return res.status(500).json({ error: 'Failed to extract features and train model.' });
      }
      console.log('[AUTO-LEARN] Output:', stdout);
      res.json({ success: true, message: `Successfully extracted landmarks and trained model for sign: ${label}` });
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`Backend server running on http://0.0.0.0:${PORT}`);
});
