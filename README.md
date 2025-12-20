# Quickpark
Quickpark is an **LPR system** (a "license-plate reader"!) that recognizes  
license plates with a YOLOv11 checkpoint and asks Qwen3 to do recognition.  
That's all. I made it in 4 nights!  

## *Build instructions soon!*

Check out the exact models I'm currently using here:
- [ https://huggingface.co/morsetechlab/yolov11-license-plate-detection ].  
    Get `license-plate-finetune-v1n.pt`.
  
- [ https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct-GGUF ].  
    Grab these!:  
    - mmproj-Qwen3VL-2B-Instruct-Q8_0.gguf
    - Qwen3VL-2B-Instruct-Q4_K_M.gguf

# *How, though?*
This code runs a single "Quickpark Unit". An ESP32-CAM hosts an HTTP server that a Python client running on a "domestic" PC connects to, and said PC runs Qwen3 VL under llama.cpp *and* also YOLOv11 to run funny LPR processes.  
  
Lastly, an Express.js app serves these with a two-button webpage.  

### *TODO!:*  
- Try to clean up after Qwen! Vehicle license numbers read should be cleaned up by a worker (likely a Node process!).  
- Rate limiting doesn't exist! It SHOULD exist! Are we seriously running an LLM EVERY frame of video?!
- ESP32-CAM really could use UDP for images. WebSockets *are* wonky ;)!  
(...I like to call them "wocks" :>!)  
