; ModuleID = 'ir.bc'

define { i8*, i8*, i8*, i8*, i8*, i8*, i8*, [2 x i64] }* @trace({ i8*, i8*, i8*, i8*, i8*, i8*, i8*, [2 x i64] }* %0, i8* %1) {
entry:
  %array = alloca [2 x i64], align 8
  %arg_ptr_1 = getelementptr { i8*, i8*, i8*, i8*, i8*, i8*, i8*, [2 x i64] }, { i8*, i8*, i8*, i8*, i8*, i8*, i8*, [2 x i64] }* %0, i32 0, i32 7, i32 1
  %arg_1 = load i64, i64* %arg_ptr_1, align 4
  br label %loop_header_0

bailout:                                          ; preds = %loop_header_0
  %bailout_phi_0 = phi i64 [ 1, %loop_header_0 ]
  %bailout_phi_1 = phi i64 [ %"2", %loop_header_0 ]
  %array_elem_ptr = getelementptr [2 x i64], [2 x i64]* %array, i32 0, i32 0
  store i64 %bailout_phi_0, i64* %array_elem_ptr, align 4
  %array_elem_ptr1 = getelementptr [2 x i64], [2 x i64]* %array, i32 0, i32 1
  store i64 %bailout_phi_1, i64* %array_elem_ptr1, align 4
  %array_elem_ptr2 = getelementptr [2 x i64], [2 x i64]* %array, i32 0, i32 0
  %array_elem = load i64, i64* %array_elem_ptr2, align 4
  %array_elem_ptr3 = getelementptr [2 x i64], [2 x i64]* %array, i32 0, i32 1
  %failarg_array = getelementptr { i8*, i8*, i8*, i8*, i8*, i8*, i8*, [2 x i64] }, { i8*, i8*, i8*, i8*, i8*, i8*, i8*, [2 x i64] }* %0, i32 0, i32 7, i32 0
  %2 = bitcast i64* %failarg_array to i8*
  %3 = bitcast i64* %array_elem_ptr3 to i8*
  call void @llvm.memcpy.p0i8.p0i8.i64(i8* align 8 %2, i8* align 8 %3, i64 %array_elem, i1 false)
  ret { i8*, i8*, i8*, i8*, i8*, i8*, i8*, [2 x i64] }* %0

loop_header_0:                                    ; preds = %resume_4, %entry
  %phi_0_1 = phi i64 [ %arg_1, %entry ], [ %"2", %resume_4 ]
  %"2" = add i64 %phi_0_1, 1
  %"3" = icmp sle i64 %"2", 9
  br i1 %"3", label %resume_4, label %bailout

resume_4:                                         ; preds = %loop_header_0
  br label %loop_header_0
}

; Function Attrs: argmemonly nounwind willreturn
declare void @llvm.memcpy.p0i8.p0i8.i64(i8* noalias nocapture writeonly, i8* noalias nocapture readonly, i64, i1 immarg) #0

attributes #0 = { argmemonly nounwind willreturn }
