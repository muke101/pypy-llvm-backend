class LLVMOptimiser:
    def __init__(self, cpu):
        self.cpu = cpu
        self.llvm = cpu.llvm
        self.debug = cpu.debug
        self.pass_manager = self.llvm.CreatePassManager(None)

    def populate_default_passes(self):
        self.llvm.AddInstructionCombiningPass(self.pass_manager)
        self.llvm.AddReassociatePass(self.pass_manager)
        self.llvm.AddGVNPass(self.pass_manager)
        self.llvm.AddScalarReplAggregatesPass(self.pass_manager)
        self.llvm.AddIndVarSimplifyPass(self.pass_manager)
        self.llvm.AddCFGSimplificationPass(self.pass_manager)

    def run_default_passes(self, module, populate=False):
        if populate:
            self.populate_default_passes()
        self.llvm.RunPassManager(self.pass_manager, module)
        if self.debug:
            self.cpu.write_ir(module, "opt")
