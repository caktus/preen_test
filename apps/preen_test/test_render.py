from preen import block
from apps.preen_test.blocks import blocks
analyzer = block.BlockAnalyzer(blocks.ManualLinkTileBlock)
renderer = block.BlockRenderer(analyzer)
renderer.simple_fake()