(function() {
  function onlyDigits(s) { return (s || '').replace(/\D+/g, ''); }

  function maskCNPJ(v) {
    var d = onlyDigits(v).slice(0, 14);
    if (d.length <= 2) return d;
    if (d.length <= 5) return d.replace(/(\d{2})(\d+)/, '$1.$2');
    if (d.length <= 8) return d.replace(/(\d{2})(\d{3})(\d+)/, '$1.$2.$3');
    if (d.length <= 12) return d.replace(/(\d{2})(\d{3})(\d{3})(\d{1,4})/, '$1.$2.$3/$4');
    return d.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{0,2}).*/, function(_, a,b,c,d,e){
      return a + '.' + b + '.' + c + '/' + d + (e ? '-' + e : '');
    });
  }

  // IE masks by UF (best-effort display only)
  function maskIEGeneric(v) {
    var d = onlyDigits(v).slice(0, 14);
    return d.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  }

  function maskIESP(v) {
    var raw = (v || '').toUpperCase().trim();
    if (raw === 'ISENTO') return 'ISENTO';
    var hasP = raw.startsWith('P');
    var d = onlyDigits(hasP ? raw.slice(1) : raw).slice(0, 12);
    var base;
    if (d.length === 12) {
      base = d.slice(0,3)+'.'+d.slice(3,6)+'.'+d.slice(6,9)+'.'+d.slice(9,12);
    } else {
      base = d.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    }
    return hasP ? ('P.' + base) : base;
  }

  function maskIEByUF(v, uf) {
    uf = (uf || '').toUpperCase();
    if (uf === 'SP') return maskIESP(v);
    // TODO: extend with more UF-specific masks
    return maskIEGeneric(v);
  }

  function applyDynamicIEMask() {
    var ieEl = document.getElementById('id_inscricao_estadual');
    var ufEl = document.getElementById('id_address_uf');
    if (!ieEl) return;

    function currentUF() { return ufEl ? (ufEl.value || '').toUpperCase() : ''; }

    function handler() {
      var start = ieEl.selectionStart;
      var before = ieEl.value;
      ieEl.value = maskIEByUF(ieEl.value, currentUF());
      try { ieEl.selectionEnd = ieEl.selectionStart = start + (ieEl.value.length - before.length); } catch (e) {}
    }

    ieEl.addEventListener('input', handler);
    if (ufEl) ufEl.addEventListener('change', handler);
    handler();
  }

  function ready(fn) {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }

  ready(function() {
    var cnpjEl = document.getElementById('id_cnpj');
    if (cnpjEl) {
      function cnpjHandler() {
        var start = cnpjEl.selectionStart;
        var before = cnpjEl.value;
        cnpjEl.value = maskCNPJ(cnpjEl.value);
        try { cnpjEl.selectionEnd = cnpjEl.selectionStart = start + (cnpjEl.value.length - before.length); } catch (e) {}
      }
      cnpjEl.addEventListener('input', cnpjHandler);
      cnpjHandler();
    }

    applyDynamicIEMask();
  });
})();
