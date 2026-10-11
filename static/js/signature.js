document.addEventListener('DOMContentLoaded', () => {
  const canvas = document.getElementById('signatureCanvas');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  const clearBtn = document.getElementById('clearSignatureBtn');
  const signatureInput = document.getElementById('signature_data');
  const mainForm = document.getElementById('policyForm');
  const sigGuideText = document.querySelector('.signature-guide-text');

  let isDrawing = false;
  let hasDrawn = false;
  let lastX = 0;
  let lastY = 0;

  function resizeCanvas() {
    const ratio = Math.max(window.devicePixelRatio || 1, 1);
    const rect = canvas.getBoundingClientRect();
    
    // Save current content if already drawn
    let tempCanvas = null;
    if (hasDrawn && canvas.width > 0 && canvas.height > 0) {
      tempCanvas = document.createElement('canvas');
      tempCanvas.width = canvas.width;
      tempCanvas.height = canvas.height;
      tempCanvas.getContext('2d').drawImage(canvas, 0, 0);
    }

    canvas.width = rect.width * ratio;
    canvas.height = rect.height * ratio;
    
    ctx.scale(ratio, ratio);
    ctx.strokeStyle = '#0a1d37';
    ctx.lineWidth = 2.5;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';

    if (tempCanvas && hasDrawn) {
      ctx.drawImage(tempCanvas, 0, 0, rect.width, rect.height);
    }
  }

  // Initial resize
  resizeCanvas();
  window.addEventListener('resize', resizeCanvas);

  function getCoordinates(e) {
    const rect = canvas.getBoundingClientRect();
    let clientX, clientY;

    if (e.touches && e.touches.length > 0) {
      clientX = e.touches[0].clientX;
      clientY = e.touches[0].clientY;
    } else {
      clientX = e.clientX;
      clientY = e.clientY;
    }

    return {
      x: clientX - rect.left,
      y: clientY - rect.top
    };
  }

  function startDrawing(e) {
    e.preventDefault();
    isDrawing = true;
    const coords = getCoordinates(e);
    lastX = coords.x;
    lastY = coords.y;
    if (sigGuideText) sigGuideText.style.display = 'none';
  }

  function draw(e) {
    if (!isDrawing) return;
    e.preventDefault();

    const coords = getCoordinates(e);
    ctx.beginPath();
    ctx.moveTo(lastX, lastY);
    ctx.lineTo(coords.x, coords.y);
    ctx.stroke();

    lastX = coords.x;
    lastY = coords.y;
    hasDrawn = true;
  }

  function stopDrawing(e) {
    if (isDrawing) {
      isDrawing = false;
      ctx.closePath();
    }
  }

  // Mouse events
  canvas.addEventListener('mousedown', startDrawing);
  canvas.addEventListener('mousemove', draw);
  window.addEventListener('mouseup', stopDrawing);

  // Touch events
  canvas.addEventListener('touchstart', startDrawing, { passive: false });
  canvas.addEventListener('touchmove', draw, { passive: false });
  window.addEventListener('touchend', stopDrawing);
  window.addEventListener('touchcancel', stopDrawing);

  // Clear button
  if (clearBtn) {
    clearBtn.addEventListener('click', (e) => {
      e.preventDefault();
      ctx.save();
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.restore();
      hasDrawn = false;
      signatureInput.value = '';
      if (sigGuideText) sigGuideText.style.display = 'block';
    });
  }

  // Form submit handling
  if (mainForm) {
    mainForm.addEventListener('submit', (e) => {
      if (hasDrawn) {
        // Export high resolution PNG data URL
        const dataURL = canvas.toDataURL('image/png');
        signatureInput.value = dataURL;
      } else {
        signatureInput.value = '';
      }
    });
  }
});
