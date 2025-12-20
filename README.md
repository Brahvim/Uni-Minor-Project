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
    - `mmproj-Qwen3VL-2B-Instruct-Q8_0.gguf`,
    - `Qwen3VL-2B-Instruct-Q4_K_M.gguf`.
  
# *How, though?*
This code runs a single "Quickpark Unit". An ESP32-CAM capturing *highly*-compressed 480p JPEG images, hosts an HTTP server, that a Python client running on a "domestic" PC connects to, and said PC runs Qwen3 VL under llama.cpp *and* also YOLOv11 to run funny LPR processes.  
Yes, said ESP32-CAM does not capture image data when no clients are connected.  
Code for that can be better, but its instruction count seems okay.  
Can still simplify the whole procedure, however. BAD loop!  
  
The DB in use here is MariaDB. Essentially MySQL if you don't know MariaDB!  
  
Lastly, an Express.js app serves these with a two-button webpage.  
  
  
### *TODO!:*  
- Try to clean up after Qwen! Vehicle license numbers read should be cleaned up by a worker (likely a Node process!).  
- Rate limiting doesn't exist! It SHOULD exist! Are we seriously running an LLM EVERY frame of video?!
- ESP32-CAM really could use UDP for images. WebSockets *are* wonky ;)!  
(...I like to call them "wocks" :>!)  
  
# Performance...?

Openly speaking: Things **need** to be tuned a lot and these numbers are NOT real benchmarks!:  
  
On my HP Pavilion 15 running Debian 13, a GTX 1650 (TU117M) GPU,  
Loading the YOLOv11 checkpoint (~5.2 MiB) and loading 2 layers of the 8-bit quant of the  
2B Qwen 3 VL-Instruct model (5+ GiB) results in ~3.6 GiB of VRAM usage; the GPU has 4.
  
Image decoding seems to take `llama-mtmd`/`llama-server` about 360ms.  
It takes **one** to **three** seconds to go from "Plate seen!" to *"License number in DB!".*  
The ESP32-CAM code surely can improve image throughput! MariaDB optimizations could be made, though I'm sure the DB already did those knowing the access pattern is just so simple. Lastly, we can make optimizations for... possibly, threading, in the Python server. Maybe also use a simpler model for all the data?  
  
As for Qwen, I may have to switch to a bigger model. 4B or greater, but below 8B for sure, ...*if* that makes the vision adapter better too. Inference optimizations could be made with some flags. As always, this depends on the exact computer and I can't say much.  
  