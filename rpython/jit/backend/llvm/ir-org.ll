; ModuleID = 'ir-org.bc'
source_filename = "trace"
target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"

define { i8*, i64, i8*, i8*, i8*, i8*, i8*, [3 x i64] }* @trace({ i8*, i64, i8*, i8*, i8*, i8*, i8*, [3 x i64] }* %0, i8* %1) {
entry:
  %overflow_flag = alloca i1, align 1
  store i1 false, i1* %overflow_flag, align 1
  %struct_elem_ptr = getelementptr { i8*, i64, i8*, i8*, i8*, i8*, i8*, [3 x i64] }, { i8*, i64, i8*, i8*, i8*, i8*, i8*, [3 x i64] }* %0, i32 0, i32 7, i32 1
  %struct_elem = load i64, i64* %struct_elem_ptr, align 8
  %struct_elem_ptr1 = getelementptr { i8*, i64, i8*, i8*, i8*, i8*, i8*, [3 x i64] }, { i8*, i64, i8*, i8*, i8*, i8*, i8*, [3 x i64] }* %0, i32 0, i32 7, i32 2
  %struct_elem2 = load i64, i64* %struct_elem_ptr1, align 8
  %cmp = icmp eq i64 %struct_elem, 0
  br i1 %cmp, label %call_block, label %resume_block

call_block:                                       ; preds = %entry
  %call_res = call i64 inttoptr (i64 139773784035344 to i64 (i64)*)(i64 %struct_elem2)
  br label %resume_block

resume_block:                                     ; preds = %call_block, %entry
  %cond_phi = phi i64 [ %call_res, %call_block ], [ %struct_elem, %entry ]
  %struct_elem_ptr3 = getelementptr { i8*, i64, i8*, i8*, i8*, i8*, i8*, [3 x i64] }, { i8*, i64, i8*, i8*, i8*, i8*, i8*, [3 x i64] }* %0, i32 0, i32 1
  store i64 139773544440048, i64* %struct_elem_ptr3, align 8
  %struct_elem_ptr4 = getelementptr { i8*, i64, i8*, i8*, i8*, i8*, i8*, [3 x i64] }, { i8*, i64, i8*, i8*, i8*, i8*, i8*, [3 x i64] }* %0, i32 0, i32 7, i32 1
  store i64 %cond_phi, i64* %struct_elem_ptr4, align 8
  ret { i8*, i64, i8*, i8*, i8*, i8*, i8*, [3 x i64] }* %0
}

; Function Attrs: nofree nosync nounwind readnone speculatable willreturn
declare double @llvm.fabs.f64(double) #0

; Function Attrs: nofree nosync willreturn
declare void @llvm.experimental.stackmap(i64, i32, ...) #1

attributes #0 = { nofree nosync nounwind readnone speculatable willreturn }
attributes #1 = { nofree nosync willreturn }
