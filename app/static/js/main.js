// =========================================================
// QUESTPLATFORM - INTERACTIVE JAVASCRIPT HELPERS
// =========================================================

document.addEventListener('DOMContentLoaded', () => {
  // Initialize Auto-closing alerts
  document.querySelectorAll('.alert-close').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const alert = e.target.closest('.alert');
      if (alert) {
        alert.style.opacity = '0';
        alert.style.transform = 'translateY(-10px)';
        setTimeout(() => alert.remove(), 250);
      }
    });
  });

  // Screenshot input preview
  const screenshotInput = document.getElementById('screenshot-upload');
  const previewContainer = document.getElementById('screenshot-preview-container');
  const previewImage = document.getElementById('screenshot-preview-img');

  if (screenshotInput && previewContainer && previewImage) {
    screenshotInput.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = (event) => {
          previewImage.src = event.target.result;
          previewContainer.style.display = 'block';
        };
        reader.readAsDataURL(file);
      } else {
        previewContainer.style.display = 'none';
      }
    });
  }
});

// Copy text to clipboard with tooltip animation
function copyToClipboard(text, btnElement) {
  if (!navigator.clipboard) {
    // Fallback for older browsers
    const textarea = document.createElement('textarea');
    textarea.value = text;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);
    showCopyFeedback(btnElement);
    return;
  }

  navigator.clipboard.writeText(text).then(() => {
    showCopyFeedback(btnElement);
  }).catch(err => {
    console.error('Failed to copy text: ', err);
  });
}

function showCopyFeedback(btnElement) {
  if (!btnElement) return;
  const originalHtml = btnElement.innerHTML;
  btnElement.innerHTML = `<span>✓ Copied!</span>`;
  btnElement.classList.add('btn-emerald');
  setTimeout(() => {
    btnElement.innerHTML = originalHtml;
    btnElement.classList.remove('btn-emerald');
  }, 2000);
}

// Modal handling
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove('active');
    document.body.style.overflow = '';
  }
}

// Close modal on click outside card
document.addEventListener('click', (e) => {
  if (e.target.classList.contains('modal-backdrop')) {
    e.target.classList.remove('active');
    document.body.style.overflow = '';
  }
});

// Lightbox Viewer
function openLightbox(imageSrc, title) {
  let lightbox = document.getElementById('global-lightbox');
  if (!lightbox) {
    lightbox = document.createElement('div');
    lightbox.id = 'global-lightbox';
    lightbox.className = 'modal-backdrop';
    lightbox.innerHTML = `
      <div class="modal-card" style="max-width: 900px; text-align: center; background: #0b0f19;">
        <div class="modal-header">
          <h3 id="lightbox-title" style="font-size: 1.1rem; color: #fff;">Proof Screenshot</h3>
          <button class="alert-close" onclick="closeModal('global-lightbox')">&times;</button>
        </div>
        <div class="modal-body" style="padding: 1rem;">
          <img id="lightbox-img" src="" alt="Proof" style="max-width: 100%; max-height: 75vh; border-radius: 8px; object-fit: contain; box-shadow: 0 4px 20px rgba(0,0,0,0.6);" />
        </div>
      </div>
    `;
    document.body.appendChild(lightbox);
  }

  document.getElementById('lightbox-img').src = imageSrc;
  document.getElementById('lightbox-title').textContent = title || 'Proof Screenshot';
  openModal('global-lightbox');
}
