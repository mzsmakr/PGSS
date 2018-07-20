#!/bin/bash
for filename in *.png; do
    convert $filename -alpha extract -threshold 90% -negate -transparent white b_$filename
    convert b_$filename +level-colors "rgb(38,66,90)", -transparent white b_$filename
    mv $filename c_$filename
done

