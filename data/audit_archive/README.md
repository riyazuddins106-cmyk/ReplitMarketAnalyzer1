# MLAI attached asset archive

The original attached binary files are preserved in `mlai_attached_assets.tar.gz.part-00` through `part-05`.

Reassemble locally with:

```sh
cat mlai_attached_assets.tar.gz.part-* > mlai_attached_assets.tar.gz
tar -xzf mlai_attached_assets.tar.gz
```

The runtime copies are also available directly under `data/`: `market_data.bin`, `candle_language_v2.bin`, and `candle_language_v2.pre_correction_backup.bin`.

Archive SHA-256: `4f73c81007e5c262bfb3a401ab872d3288cae0482e500136117f5fbbd0d3b05a`.
