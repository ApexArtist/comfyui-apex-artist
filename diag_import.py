import runpy
import traceback
import glob

py_files = glob.glob('*.py')
errors = False
for p in sorted(py_files):
    if p == 'diag_import.py':
        continue
    try:
        runpy.run_path(p, run_name='__main__')
        print(f'OK: {p}')
    except Exception as e:
        errors = True
        print(f'ERROR importing {p}:')
        traceback.print_exc()

if not errors:
    print('\nAll files imported without exceptions.')
else:
    print('\nOne or more files failed to import.')
