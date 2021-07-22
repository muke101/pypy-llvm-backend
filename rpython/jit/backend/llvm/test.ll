; ModuleID = '<stdin>'
source_filename = "<stdin>"

define { i8*, i8*, i8*, i8*, i8*, i8*, i8*, [4 x i64] }* @trace({ i8*, i8*, i8*, i8*, i8*, i8*, i8*, [4 x i64] }* %0, i8* %1) {
entry:
  %arg_ptr_1 = getelementptr { i8*, i8*, i8*, i8*, i8*, i8*, i8*, [4 x i64] }, { i8*, i8*, i8*, i8*, i8*, i8*, i8*, [4 x i64] }* %0, i64 0, i32 7, i64 1
  %arg_1 = load i64, i64* %arg_ptr_1, align 4
  %arg_ptr_2 = getelementptr { i8*, i8*, i8*, i8*, i8*, i8*, i8*, [4 x i64] }, { i8*, i8*, i8*, i8*, i8*, i8*, i8*, [4 x i64] }* %0, i64 0, i32 7, i64 2
  %arg_2 = load i64, i64* %arg_ptr_2, align 4
  %arg_ptr_3 = getelementptr { i8*, i8*, i8*, i8*, i8*, i8*, i8*, [4 x i64] }, { i8*, i8*, i8*, i8*, i8*, i8*, i8*, [4 x i64] }* %0, i64 0, i32 7, i64 3
  %arg_3 = load i64, i64* %arg_ptr_3, align 4
  br label %loop_header_0

bailout:                                          ; preds = %loop_header_0
  %final_descr = getelementptr { i8*, i8*, i8*, i8*, i8*, i8*, i8*, [4 x i64] }, { i8*, i8*, i8*, i8*, i8*, i8*, i8*, [4 x i64] }* %0, i64 0, i32 1
  store i8* inttoptr (i64 140428050964640 to i8*), i8** %final_descr, align 8
  %2 = bitcast i64* %arg_ptr_1 to i8*
  %3 = trunc i64 %"4" to i8
  store i8 %3, i8* %2, align 8
  ret { i8*, i8*, i8*, i8*, i8*, i8*, i8*, [4 x i64] }* %0

loop_header_0:                                    ; preds = %loop_header_0, %entry
  %phi_0_1 = phi i64 [ %arg_1, %entry ], [ %"4", %loop_header_0 ]
  %phi_1_2 = phi i64 [ %arg_2, %entry ], [ %"5", %loop_header_0 ]
  %phi_2_3 = phi i64 [ %arg_3, %entry ], [ %"6", %loop_header_0 ]
  %"4" = add i64 %phi_1_2, %phi_0_1
  %"5" = add i64 %"4", 1
  %"6" = add i64 %"5", %phi_0_1
  %"7.not" = icmp sgt i64 %"6", %phi_2_3
  br i1 %"7.not", label %bailout, label %loop_header_0
}

; Function Attrs: argmemonly nounwind willreturn
declare void @llvm.memcpy.p0i8.p0i8.i64(i8* noalias nocapture writeonly, i8* noalias nocapture readonly, i64, i1 immarg) #0

attributes #0 = { argmemonly nounwind willreturn }
