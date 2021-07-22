; ModuleID = '<stdin>'
source_filename = "trace"
target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"

; Function Attrs: nofree norecurse nounwind willreturn
define { i8*, i64, i8*, i8*, i8*, i8*, i8*, [3 x i64] }* @trace({ i8*, i64, i8*, i8*, i8*, i8*, i8*, [3 x i64] }* returned %0, i8* nocapture readnone %1) local_unnamed_addr #0 {
entry:
  %struct_elem_ptr = getelementptr { i8*, i64, i8*, i8*, i8*, i8*, i8*, [3 x i64] }, { i8*, i64, i8*, i8*, i8*, i8*, i8*, [3 x i64] }* %0, i64 0, i32 7, i64 1
  %struct_elem = load i64, i64* %struct_elem_ptr, align 8
  %struct_elem_ptr1 = getelementptr { i8*, i64, i8*, i8*, i8*, i8*, i8*, [3 x i64] }, { i8*, i64, i8*, i8*, i8*, i8*, i8*, [3 x i64] }* %0, i64 0, i32 7, i64 2
  %struct_elem2 = load i64, i64* %struct_elem_ptr1, align 8
  %a_high = lshr i64 %struct_elem, 4
  %a_low = and i64 %struct_elem, 15
  %b_high = lshr i64 %struct_elem2, 4
  %b_low = and i64 %struct_elem2, 15
  %res_low_low = mul nuw nsw i64 %b_low, %a_low
  %res_low_high = mul nuw i64 %b_high, %a_low
  %res_high_low = mul nuw i64 %b_low, %a_high
  %res_high_high = mul i64 %b_high, %a_high
  %res = lshr i64 %res_low_low, 4
  %res3 = add i64 %res_low_high, %res_high_low
  %res4 = add i64 %res3, %res
  %cmp = icmp ugt i64 %res4, %res
  %borrow = select i1 %cmp, i64 0, i64 16
  %res5 = lshr i64 %res4, 4
  %res6 = add i64 %res5, %res_high_high
  %uint_mul_high_res = add i64 %res6, %borrow
  %struct_elem_ptr7 = getelementptr { i8*, i64, i8*, i8*, i8*, i8*, i8*, [3 x i64] }, { i8*, i64, i8*, i8*, i8*, i8*, i8*, [3 x i64] }* %0, i64 0, i32 1
  store i64 139786752766432, i64* %struct_elem_ptr7, align 8
  store i64 %uint_mul_high_res, i64* %struct_elem_ptr, align 8
  ret { i8*, i64, i8*, i8*, i8*, i8*, i8*, [3 x i64] }* %0
}

attributes #0 = { nofree norecurse nounwind willreturn }
