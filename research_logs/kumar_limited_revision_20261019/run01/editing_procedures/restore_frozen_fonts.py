"""Restore only frozen, previously used Arial/Times font archives privately."""
from pathlib import Path
import ctypes as C
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = Path('/workspace/few-shot-mi-eeg')
source = ROOT/'research_logs/kumar_plos_final_submission_20261017/final_submission_font_restore_receipt_20261017.json'
frozen = json.loads(source.read_text())
expected = {v['file']:v for v in frozen['files']}
out = HERE/'restored_fonts'
out.mkdir(exist_ok=True)
lib=C.CDLL('libarchive.so.13')
lib.archive_read_new.restype=C.c_void_p
lib.archive_read_support_format_cab.argtypes=[C.c_void_p]
lib.archive_read_support_filter_all.argtypes=[C.c_void_p]
lib.archive_read_open_memory.argtypes=[C.c_void_p,C.c_void_p,C.c_size_t]
lib.archive_read_next_header.argtypes=[C.c_void_p,C.POINTER(C.c_void_p)]
lib.archive_entry_pathname.argtypes=[C.c_void_p]
lib.archive_entry_pathname.restype=C.c_char_p
lib.archive_read_data.argtypes=[C.c_void_p,C.c_void_p,C.c_size_t]
lib.archive_read_data.restype=C.c_ssize_t
lib.archive_read_free.argtypes=[C.c_void_p]
restored=[]
for archive in frozen['archives']:
    name=archive['file']
    data=(HERE/'font_archives'/name).read_bytes()
    assert hashlib.sha256(data).hexdigest()==archive['sha256']
    pos=data.index(b'MSCF\x00\x00\x00\x00')
    memory=C.create_string_buffer(data[pos:])
    reader=lib.archive_read_new()
    lib.archive_read_support_format_cab(reader)
    lib.archive_read_support_filter_all(reader)
    assert lib.archive_read_open_memory(reader,memory,len(memory))==0
    while True:
        entry=C.c_void_p()
        code=lib.archive_read_next_header(reader,C.byref(entry))
        if code==1: break
        assert code==0,code
        filename=Path(lib.archive_entry_pathname(entry).decode()).name
        chunks=[]
        while True:
            buf=C.create_string_buffer(65536)
            count=lib.archive_read_data(reader,buf,len(buf))
            assert count>=0
            if not count: break
            chunks.append(buf.raw[:count])
        if filename not in expected: continue
        payload=b''.join(chunks)
        actual=hashlib.sha256(payload).hexdigest()
        assert len(payload)==expected[filename]['bytes']
        assert actual==expected[filename]['sha256']
        (out/filename).write_bytes(payload)
        restored.append({'file':str(out/filename),'bytes':len(payload),'sha256':actual})
    lib.archive_read_free(reader)
assert len(restored)==8
(HERE/'font_restore_receipt.json').write_text(json.dumps({
    'status':'all_eight_font_files_match_frozen_20261017_hashes',
    'frozen_receipt':str(source),'archives':frozen['archives'],
    'fonts':restored,'fonts_in_git':False,'global_installation':False,
},indent=2)+'\n')
print(json.dumps({'fonts':len(restored),'path':str(out)}))
