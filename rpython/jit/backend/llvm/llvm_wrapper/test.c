#include "wrapper.h"

int main()	{
	LLVMModuleRef module = LLVMModuleCreateWithName("module");
	LLVMTypeRef arg_types[] = {LLVMInt32Type()};
	LLVMTypeRef ret_type = LLVMFunctionType(LLVMInt32Type(), arg_types, 1, 0);
	LLVMValueRef test = LLVMAddFunction(module, "test", ret_type);
	LLVMBasicBlockRef entry = LLVMAppendBasicBlock(test, "entry");
	LLVMBuilderRef builder = LLVMCreateBuilder();
	LLVMPositionBuilderAtEnd(builder, entry);

	LLVMTypeRef array = LLVMArrayType(LLVMIntType(32), 10);
	LLVMValueRef arr = LLVMBuildAlloca(builder, array, "array");
	LLVMValueRef indecies[2] = {LLVMConstInt(LLVMInt32Type(), 0, 0), LLVMConstInt(LLVMInt32Type(), 1, 0)};
	LLVMValueRef gep = LLVMBuildGEP2(builder, array, arr, indecies, 2, "gep");
	LLVMTypeRef res_type = getIndexedType(gep, array, indecies);
	LLVMDumpType(res_type);
}
