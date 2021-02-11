## acb.py

For all your ACB extracting needs. Based on [VGMToolbox](https://sourceforge.net/projects/vgmtoolbox/).

HCA decryption is based on the 2ch HCA decoder. Thanks also to Headcrabbed who documented the new extra key [here](https://blog.mottomo.moe/categories/Tech/RE/en/2018-10-12-New-HCA-Encryption/).

Usage:

```sh
python3 setup.py install
python3 -m acb somefile.acb output
# equivalent
acbextract somefile.acb output
```

You can also pass `--disarm-with=key1,key2` to have the library decrypt (but not decode) files for you. The key format
`--disarm-with=k1,k2` is equivalent to `hca_decoder -a k1 -b k2`, but you can also combine them into a 64-bit hex integer.
This also supports AWB embedded keys (see [here](https://github.com/hozuki/libcgss/issues/4)).
If you use disarm heavily, you should also install the `_acb_speedup` C extension in the `fast_sub`
directory. It will substantially speed up the decryption process.