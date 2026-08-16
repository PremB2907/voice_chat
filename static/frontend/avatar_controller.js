import { VISEME_MAP } from './viseme_map.js';

export class AvatarController {
  constructor(avatarModel, globalAudio) {
    this.avatarModel = avatarModel;
    this.globalAudio = globalAudio;
    
    this.faceMesh = null;
    this.morphTargets = {};
    this.morphInfluences = null;
    
    // Viseme cues
    this.cues = [];
    this.activeViseme = 'REST';
    this.nextViseme = 'REST';
    this.smoothingFactor = 0.25; // Easing parameter to prevent mouth snapping
    
    // Blink state
    this.blinkTimer = 0.0;
    this.nextBlinkTime = 3.0 + Math.random() * 3.0; // Random blinks every 3-6s
    this.blinkDuration = 0.15; // 150ms blink duration
    this.isBlinking = false;
    
    // Emotion target offsets
    this.currentEmotion = 'neutral';
    this.emotionOffsets = {
      mouthSmileLeft: 0,
      mouthSmileRight: 0,
      mouthFrownLeft: 0,
      mouthFrownRight: 0,
      browDownLeft: 0,
      browDownRight: 0
    };
    
    // Fallback Web Audio RMS
    this.audioCtx = null;
    this.analyser = null;
    this.dataArray = null;
    this.audioSource = null;
    this.fallbackInitialized = false;

    this._discoverFacialGeometry();
  }

  _discoverFacialGeometry() {
    if (!this.avatarModel) return;
    
    console.log("🔍 Scanning GLB for facial morph meshes...");
    this.avatarModel.traverse((child) => {
      if ((child.isMesh || child.isSkinnedMesh) && child.morphTargetDictionary) {
        // Avaturn body mesh contains the blendshapes
        const keys = Object.keys(child.morphTargetDictionary);
        if (keys.includes("jawOpen") || child.name.includes("body")) {
          this.faceMesh = child;
          this.morphTargets = child.morphTargetDictionary;
          this.morphInfluences = child.morphTargetInfluences;
          console.log(`🎭 Facial mesh identified: "${child.name}" with ${keys.length} blendshapes`);
          
          // Debug keys sample
          console.log("Blendshape samples:", keys.slice(0, 10));
        }
      }
    });

    if (!this.faceMesh) {
      console.warn("⚠️ No facial mesh containing blendshapes found in the GLB!");
    }
  }

  loadVisemes(cues) {
    this.cues = cues || [];
    console.log(`📥 Loaded ${this.cues.length} lip-sync cues into viseme controller.`);
  }

  setEmotion(emotion) {
    if (!emotion) return;
    this.currentEmotion = emotion.toLowerCase();
    
    // Reset offsets
    this.emotionOffsets = {
      mouthSmileLeft: 0,
      mouthSmileRight: 0,
      mouthFrownLeft: 0,
      mouthFrownRight: 0,
      browDownLeft: 0,
      browDownRight: 0
    };

    // Apply additive offsets depending on emotion
    if (this.currentEmotion === 'joy' || this.currentEmotion === 'happy') {
      this.emotionOffsets.mouthSmileLeft = 0.35;
      this.emotionOffsets.mouthSmileRight = 0.35;
    } else if (this.currentEmotion === 'sad' || this.currentEmotion === 'sadness') {
      this.emotionOffsets.mouthFrownLeft = 0.45;
      this.emotionOffsets.mouthFrownRight = 0.45;
      this.emotionOffsets.browDownLeft = 0.15;
      this.emotionOffsets.browDownRight = 0.15;
    } else if (this.currentEmotion === 'anger' || this.currentEmotion === 'angry') {
      this.emotionOffsets.browDownLeft = 0.55;
      this.emotionOffsets.browDownRight = 0.55;
      this.emotionOffsets.mouthFrownLeft = 0.25;
      this.emotionOffsets.mouthFrownRight = 0.25;
    }
    
    console.log(`🎭 Emotion layer updated: "${this.currentEmotion}"`);
  }

  forceViseme(visemeName) {
    if (!this.faceMesh || !this.morphTargets || !this.morphInfluences) return;
    this.activeViseme = visemeName;
    this.cues = []; // Clear current cues
    
    // Instantly map target viseme morph weights
    const visemeWeights = VISEME_MAP[visemeName] || VISEME_MAP.REST;
    
    // Reset all viseme keys first
    Object.keys(VISEME_MAP.REST).forEach(key => {
      const idx = this.morphTargets[key];
      if (idx !== undefined) this.morphInfluences[idx] = 0.0;
    });

    // Apply forced weights
    Object.keys(visemeWeights).forEach(key => {
      const idx = this.morphTargets[key];
      if (idx !== undefined) {
        this.morphInfluences[idx] = visemeWeights[key];
      }
    });
    console.log(`🔧 Viseme manually forced: "${visemeName}"`);
  }

  _initAudioFallback() {
    if (this.fallbackInitialized) return;
    try {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      this.audioCtx = new AudioContextClass();
      this.analyser = this.audioCtx.createAnalyser();
      this.analyser.fftSize = 256;
      this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);
      
      // Connect globalAudio to analyser
      this.audioSource = this.audioCtx.createMediaElementSource(this.globalAudio);
      this.audioSource.connect(this.analyser);
      this.analyser.connect(this.audioCtx.destination);
      
      this.fallbackInitialized = true;
      console.log("🔊 Web Audio RMS Fallback Initialized.");
    } catch (e) {
      console.warn("⚠️ Failed to initialize audio context fallback:", e);
    }
  }

  _getAudioRMS() {
    if (!this.fallbackInitialized || !this.analyser) return 0;
    this.analyser.getByteFrequencyData(this.dataArray);
    let sum = 0;
    for (let i = 0; i < this.dataArray.length; i++) {
      sum += this.dataArray[i];
    }
    return sum / this.dataArray.length;
  }

  update(delta, elapsedTime) {
    if (!this.faceMesh || !this.morphTargets || !this.morphInfluences) return;

    // Target weights for the active frame
    const targets = {};
    
    // Initialize targets with REST values
    Object.keys(VISEME_MAP.REST).forEach(key => {
      targets[key] = 0.0;
    });

    // ═══ LAYER 1: SPEECH LIP-SYNC ═══
    const isPlaying = this.globalAudio && !this.globalAudio.paused && !this.globalAudio.ended;
    
    if (isPlaying && this.cues.length > 0) {
      const time = this.globalAudio.currentTime;
      
      // Find the active cue
      let activeCue = null;
      for (let i = 0; i < this.cues.length; i++) {
        const cue = this.cues[i];
        if (time >= cue.start && time <= cue.end) {
          activeCue = cue;
          this.activeViseme = cue.value;
          this.nextViseme = (i + 1 < this.cues.length) ? this.cues[i + 1].value : 'REST';
          break;
        }
      }

      if (!activeCue) {
        this.activeViseme = 'REST';
      }

      // Map viseme to target morph weights
      const visemeWeights = VISEME_MAP[this.activeViseme] || VISEME_MAP.REST;
      Object.keys(visemeWeights).forEach(key => {
        targets[key] = visemeWeights[key];
      });

    } else if (isPlaying) {
      // ═══ LAYER 1b: RUNTIME AUDIO AMPLITUDE FALLBACK ═══
      this._initAudioFallback();
      if (this.audioCtx && this.audioCtx.state === 'suspended') {
        this.audioCtx.resume();
      }
      
      const rms = this._getAudioRMS(); // 0 to 255
      const normalizedRms = Math.min(1.0, rms / 120.0); // Normalize to standard speech mouth scale
      
      targets.jawOpen = normalizedRms * 0.75;
      targets.mouthClose = (1.0 - normalizedRms) * 0.2;
      this.activeViseme = 'FALLBACK_RMS';
    } else {
      this.activeViseme = 'REST';
      this.nextViseme = 'REST';
    }

    // ═══ LAYER 2: PROCEDURAL BLINKING ═══
    this.blinkTimer += delta;
    if (!this.isBlinking && this.blinkTimer >= this.nextBlinkTime) {
      this.isBlinking = true;
      this.blinkTimer = 0.0;
    }
    
    let blinkWeight = 0.0;
    if (this.isBlinking) {
      if (this.blinkTimer <= this.blinkDuration / 2) {
        // Close eyelids
        blinkWeight = this.blinkTimer / (this.blinkDuration / 2);
      } else if (this.blinkTimer <= this.blinkDuration) {
        // Open eyelids
        blinkWeight = 1.0 - ((this.blinkTimer - (this.blinkDuration / 2)) / (this.blinkDuration / 2));
      } else {
        // Blink finished
        this.isBlinking = false;
        this.blinkTimer = 0.0;
        this.nextBlinkTime = 2.5 + Math.random() * 4.0;
      }
    }

    // Apply blinks to targets
    targets.eyeBlinkLeft = blinkWeight;
    targets.eyeBlinkRight = blinkWeight;

    // ═══ LAYER 3: EMOTION BLENDING ═══
    Object.keys(this.emotionOffsets).forEach(key => {
      if (targets[key] !== undefined) {
        // Additive overlay for emotion
        targets[key] = Math.min(1.0, targets[key] + this.emotionOffsets[key]);
      } else {
        targets[key] = this.emotionOffsets[key];
      }
    });

    // ═══ APPLY SMOOTH INTERPOLATION (LERP) ═══
    Object.keys(targets).forEach(key => {
      const idx = this.morphTargets[key];
      if (idx !== undefined) {
        const current = this.morphInfluences[idx] || 0.0;
        const target = targets[key];
        // Apply smooth transition formula
        this.morphInfluences[idx] = current + (target - current) * this.smoothingFactor;
      }
    });
  }
}
