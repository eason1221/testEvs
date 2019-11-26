pragma solidity >=0.4.21 <0.6.0;

contract Sample {
    bytes32 public cmts_B;
    bytes32 public cmts_A;
    address public addressa;
    address public addressb;
    uint public amounts;
    uint public N;
    bytes32 public H0;
    bool commitend = false;
    bool claimend = false;

    constructor() public {

    }

    function Commit(bytes32 h0,uint amount,uint n) public {
        if(commitend==false){
            amounts = amount;
            N = n;
            H0 = h0;
            addressa = msg.sender;
            commitend = true;
        }
    }

    function Claim(bytes32 hi,uint valuesb,bytes32 cmts_b) public {
        if(commitend && claimend==false){
            uint temp;
            bytes32 myhash = hi;
            for(uint i = 0;i<10000;i++){
                bytes32 Myhash = keccak256(abi.encodePacked(myhash));
                if(Myhash == H0){
                    temp = i+1;
                    break;
                }
                else{
                    myhash = Myhash;
                }
            }
            uint value = amounts*temp/N;
            if(value == valuesb){
                amounts = amounts - value;
                addressb = msg.sender;
                cmts_B = cmts_b;
                claimend = true;
            }
        }
    }

    function Refund(uint valuesa,bytes32 cmts_a) public {
        if(claimend && msg.sender == addressa){
            if(amounts == valuesa){
                cmts_A = cmts_a;
            }

        }

    }

}

