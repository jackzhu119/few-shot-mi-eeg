# Independent local verification of the completed R2 receipt

Passed within the stated local evidence scope. The actual receipt is `completed`:
**679 unique keys / 70,070,553 payload bytes / 679 full-GET-verified rows / zero failures**.

The complete receipt is **579,221 UTF-8 bytes**, SHA256
`7eab03bf7c6d21dc9ca60a8b878f2a74051ac95af32054255d145933ae4b3770`. Its bytes remained unchanged during verification.

Every one of679 rows has a final content-verified status, full-GET verification
marker, HTTP200 and readback byte count equal to both expected and actual local
file length. Complete local file SHA256 values match the receipt and the678-entry
nonself payload manifest; the manifest itself is the679th verified object.
No duplicate key/path, missing file, extra payload file or symlink was found.
All aggregate counts and readback/upload byte sums reconcile to actual rows.

All **283 public payload files** match exact Git blobs at fixed core commit
`f2901decfc39b2adecae13253ee4b1159a4f9a4b`; 395 private evidence files and the manifest complete the679-object scope.
The private original full reviewer report remains 25,151 bytes, SHA256
`6936d14052b0dd82011d3abb8961d70066859f839e58a9448ba9585e7a53e73b`, identical to the expected original hash and both saved indices.

The uploader receipt and payload manifest still name precommit source base
`a78372db00cd4161e713ab47aca2d93c643a52bb`. This metadata was not rewritten. The separate
283-file byte comparison establishes the actual payload's binding to f2901de;
it does not relabel the earlier planning metadata or assert a new remote Git read.

This audit made **no remote GET or other network request**, read no credentials,
changed no source/payload/transport receipt, and wrote no acceptance or parent
acknowledgement. It independently read the actual completed receipt and rehashed
local bytes. The transport receipt stores expected SHA256 and the full-GET success
marker rather than a second redundant observed-digest field. The matching uploader
source `b2583bcbe67956684d1599007d6d7aa2e8ca69f817b4171dca68ddb2d34a886e` checks complete streamed GET length/digest before that
marker can be returned. This audit does not claim to have observed a second remote
response or to supply an independent remote replication.

Complete per-object local results, fixed-core blob identities and these evidence
boundaries are recorded in `independent_R2_receipt_verification.json`.
