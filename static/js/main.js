(function(){
  const modal = document.getElementById('createBookingModal');
  if (!modal) return;

  const openButtons = [
    document.getElementById('openCreateBookingModalSidebar'),
    document.getElementById('openCreateBookingModalHeader')
  ].filter(Boolean);

  const closeButton = document.getElementById('closeCreateBookingModal');
  const cancelButton = document.getElementById('cancelCreateBooking');
  const backdrop = modal.querySelector('.st-modal-backdrop');
  const form = document.getElementById('createBookingForm');

  function openCreateBookingModal(){
    modal.classList.remove('st-modal-hidden');
    modal.classList.add('st-modal-open');
    const firstInput = modal.querySelector('input, textarea, select');
    if (firstInput) firstInput.focus();
  }

  function closeCreateBookingModal(){
    modal.classList.remove('st-modal-open');
    modal.classList.add('st-modal-hidden');
    if (form) form.reset();
  }

  openButtons.forEach(btn => {
    btn.addEventListener('click', function(e){
      e.preventDefault();
      openCreateBookingModal();
    });
  });

  [closeButton, cancelButton, backdrop].forEach(el => {
    if (!el) return;
    el.addEventListener('click', function(e){
      e.preventDefault();
      closeCreateBookingModal();
    });
  });

  document.addEventListener('keydown', function(e){
    if (e.key === 'Escape' && modal.classList.contains('st-modal-open')){
      closeCreateBookingModal();
    }
  });
})();
