# Source this file, then run the frozen launcher unchanged. Dress rehearsal only (dev pool, stand-in fixture runtime).
REPO=/home/levinsonchen/project/rosa-research
RH=$REPO/research/studies/exam_dress_rehearsal_20261122
RUN=$REPO/research/_artifacts/runs/exam_dress_rehearsal_20261122
export ROSA_REHEARSAL_STUDIES=$REPO/research/studies
export ROSA_REHEARSAL_CUSTODY=$RUN/custody
export ROSA_REHEARSAL_MANIFEST=$RUN/MANIFEST_rehearsal.json
export ROSA_STAGE1_POOL=$RUN/custody/stage1_rehearsal/pool.json
export PYTHONPATH=$RH${PYTHONPATH:+:$PYTHONPATH}
export ROS_DOMAIN_ID=219 ROS_LOCALHOST_ONLY=1 ROSA_EXAM_MACHINE=laptop
BRIDGE=$REPO/research/studies/custodian_stage1_20261121/queue_bridge.py
SPEC=$RH/rehearsal_spec.json
