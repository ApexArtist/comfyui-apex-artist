import importlib.util,pathlib,sys,types,unittest
from unittest.mock import patch
import torch
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('compare_test',ROOT/'apex_compare.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class Preview:
    def __init__(self):self.calls=[]
    def save_images(self,image,filename_prefix):
        self.calls.append(image)
        return {'ui':{'images':[{'filename':filename_prefix+'.png','subfolder':'','type':'temp'}]}}
class CompareTests(unittest.TestCase):
    def test_outputs_are_originals_and_labels_are_ui_only(self):
        a=torch.rand(2,8,16,3);b=torch.rand(1,10,20,3);ac=a.clone();bc=b.clone()
        with patch.dict(sys.modules,{'nodes':types.SimpleNamespace(PreviewImage=Preview)}):n=mod.ApexCompare()
        out=n.compare(a,b,'Before','After',9)
        self.assertIs(out['result'][0],a);self.assertIs(out['result'][1],b)
        self.assertTrue(torch.equal(a,ac));self.assertTrue(torch.equal(b,bc))
        info=out['ui']['apex_compare'][0];self.assertEqual((info['label_a'],info['label_b']),('Before','After'))
        self.assertEqual((info['frame_a'],info['frame_b']),(1,0))
        self.assertEqual([x.shape[0] for x in n._preview.calls],[1,1])
    def test_preview_is_bounded_and_aspect_is_preserved(self):
        image=torch.zeros(1,600,2400,3)
        out,_=mod.preview_frame(image,0)
        self.assertEqual(list(out.shape),[1,512,2048,3])
    def test_grayscale_and_nonfinite_preview(self):
        a=torch.ones(1,2,2,1)*float('nan');out,_=mod.preview_frame(a,0)
        self.assertEqual(out.shape[-1],3);self.assertTrue(torch.isfinite(out).all())
    def test_bad_tensor_is_rejected(self):
        for value in [None,torch.zeros(3,4,4),torch.zeros(0,4,4,3),torch.zeros(1,4,4,2)]:
            with self.assertRaisesRegex(ValueError,'Apex Compare'):mod.preview_frame(value,0)
if __name__=='__main__':unittest.main()
