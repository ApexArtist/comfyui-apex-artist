"""Apply Apex's tested LTX 2.5 adjustments to a Git-installed PromptRelay."""
import argparse
from pathlib import Path
import subprocess


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--promptrelay',type=Path,default=Path(__file__).resolve().parents[2]/'ComfyUI-PromptRelay')
    parser.add_argument('--apply',action='store_true',help='Apply the patch; otherwise only check compatibility.')
    args=parser.parse_args()
    target=args.promptrelay.resolve()
    if not (target/'.git').exists():
        parser.error('Choose the Git-installed ComfyUI-PromptRelay folder.')
    patch=Path(__file__).with_name('promptrelay-ltx25.patch')
    command=['git','-C',str(target),'apply']
    check=subprocess.run([*command,'--check',str(patch)],capture_output=True,text=True)
    if check.returncode:
        reverse=subprocess.run([*command,'--reverse','--check',str(patch)],capture_output=True,text=True)
        if reverse.returncode:
            parser.error('PromptRelay differs from the tested source. No files changed.\n'+check.stderr)
        print('LTX 2.5 adjustments are already applied.')
        return
    if args.apply:
        subprocess.run([*command,str(patch)],check=True)
        print('Applied LTX 2.5 tokenizer, reference-mask and cache adjustments. Restart ComfyUI.')
    else:
        print('Patch is compatible. Add --apply to update PromptRelay.')


if __name__=='__main__':
    main()
