<template>
  <span>
    <Button
      variant="subtle"
      theme="blue"
      :label="__('Scan')"
      @click="open"
    >
      <template #prefix><LucideScanLine class="size-4" /></template>
    </Button>

    <Dialog v-model="showing" :options="{ title: __('Scan a barcode'), size: 'lg' }">
      <template #body-content>
        <div v-if="error" class="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-800">
          {{ error }}
          <p class="mt-2 text-xs text-red-700">
            {{ __("You can still type or scan the serial into the box behind this dialog - a USB scanner types like a keyboard and does not need the camera.") }}
          </p>
        </div>

        <div v-else>
          <!-- the camera feed itself; the frame is only a sighting aid -->
          <div class="relative overflow-hidden rounded-lg bg-black">
            <video ref="video" class="h-64 w-full object-cover" muted playsinline></video>
            <div class="pointer-events-none absolute inset-0 grid place-items-center">
              <div class="h-24 w-4/5 rounded-lg border-2 border-white/80 shadow-[0_0_0_9999px_rgba(0,0,0,.35)]"></div>
            </div>
          </div>
          <p class="mt-3 text-center text-sm text-ink-gray-6">
            {{ __("Hold the nameplate barcode inside the frame") }}
          </p>
        </div>
      </template>
    </Dialog>
  </span>
</template>

<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from "vue";
import { Button, Dialog } from "frappe-ui";
import { __ } from "@/translation";
import LucideScanLine from "~icons/lucide/scan-line";

const emit = defineEmits<{ (e: "scanned", value: string): void }>();

const showing = ref(false);
const error = ref("");
const video = ref<HTMLVideoElement | null>(null);
let stream: MediaStream | null = null;
let detector: any = null;
let timer: any = null;

async function open() {
  error.value = "";
  showing.value = true;

  // BarcodeDetector is what makes this work without shipping a decoder. Chrome
  // and Edge on Android have it; Firefox and iOS Safari do not, and a dealer on
  // one of those still has the text box and a USB scanner.
  if (!("BarcodeDetector" in window)) {
    error.value = __("This browser cannot use the camera to read barcodes.");
    return;
  }
  if (!navigator.mediaDevices?.getUserMedia) {
    error.value = __("This browser will not give the page a camera.");
    return;
  }

  try {
    const Detector = (window as any).BarcodeDetector;
    const formats = await Detector.getSupportedFormats();
    detector = new Detector({
      // the formats a pump nameplate actually carries
      formats: formats.filter((f: string) =>
        ["code_128", "code_39", "qr_code", "ean_13", "itf"].includes(f)
      ),
    });
    // the rear camera, which is the one pointed at the pump
    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: "environment" } },
    });
    await new Promise((r) => setTimeout(r, 0)); // let the dialog mount the <video>
    if (video.value) {
      video.value.srcObject = stream;
      await video.value.play();
    }
    timer = setInterval(read, 350);
  } catch (e: any) {
    error.value =
      e?.name === "NotAllowedError"
        ? __("The camera was blocked. Allow it for this site, or type the serial instead.")
        : __("The camera could not be opened.");
    stop();
  }
}

async function read() {
  if (!detector || !video.value || video.value.readyState !== 4) return;
  try {
    const found = await detector.detect(video.value);
    if (found?.length) {
      const value = String(found[0].rawValue || "").trim();
      if (value) {
        emit("scanned", value);
        close();
      }
    }
  } catch {
    /* a frame that will not decode is not an error worth showing */
  }
}

function stop() {
  if (timer) clearInterval(timer);
  timer = null;
  stream?.getTracks().forEach((t) => t.stop());
  stream = null;
}

function close() {
  stop();
  showing.value = false;
}

// a camera left running behind a closed dialog is a light nobody turned off
watch(showing, (v) => {
  if (!v) stop();
});

onBeforeUnmount(stop);
</script>
