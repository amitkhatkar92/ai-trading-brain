from pathlib import Path
text = Path('/tmp/orch_bak.py').read_text(encoding='utf-8')
OLD = '                _dhan.emit_feed_integrity_summary()\n        except Exception as _dhan_sum_exc:'
q = chr(34)
pct = chr(37)
nl = chr(10)
health = (
    '                _dhan.emit_feed_integrity_summary()' + nl +
    '            # -- Symbol normalization health --------------------------------' + nl +
    '            try:' + nl +
    '                from utils.symbol_utils import get_normalization_health as _gnh' + nl +
    '                from utils.symbol_utils import reset_normalization_counters as _rsc' + nl +
    '                _h = _gnh()' + nl +
    '                log.info(' + nl +
    '                    ' + q + '[SymbolNormalizationHealth] symbols_processed=' + pct + 'd symbols_normalized=' + pct + 'd ' + q + nl +
    '                    ' + q + 'normalization_rate=' + pct + '.6f lookup_failures_prevented=' + pct + 'd' + q + ',' + nl +
    '                    _h[' + q + 'symbols_processed' + q + '], _h[' + q + 'symbols_normalized' + q + '],' + nl +
    '                    _h[' + q + 'normalization_rate' + q + '], _h[' + q + 'lookup_failures_prevented' + q + '],' + nl +
    '                )' + nl +
    '                _rsc()' + nl +
    '            except Exception as _sym_e:' + nl +
    '                log.debug(' + q + '[SymbolNormalizationHealth] skipped: %s' + q + ', _sym_e)' + nl +
    '        except Exception as _dhan_sum_exc:'
)
if OLD in text:
    fixed = text.replace(OLD, health, 1)
    Path('/tmp/orch_fixed.py').write_text(fixed, encoding='utf-8')
    print('OK lines=' + str(fixed.count(chr(10))))
else:
    print('ANCHOR NOT FOUND')
