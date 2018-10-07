`timescale 1ns / 1ps
`define NULL 0

module lookupII
	#()(
		input								reset_n,	
		input								clk,	
		input     [31:0]                      time_p,
		input                             enable,
		
		input								valid,				//from 1
		input	[LENTH_WIDTH-1:0]				lenth_Data, 		//packets lenth value
		input	[ID_WIDTH-1:0]					ID_Data, 			//packets FLOW-ID
		
		input								update_c_valid,		//from 4
		input [COUNTER_WIDTH-1:0]			update_counter_data,
		input [ID_WIDTH-1:0]			 		update_ID_Data,
		
		output reg 						couter_valid,		//to 4
		output reg [COUNTER_WIDTH-1:0]		counter_data,
		output reg [LENTH_WIDTH-1:0]			lenth_Data_next,
		output reg [ID_WIDTH-1:0]			ID_Data_next,		//if any valid signals include 1,couter_update_valid 2,Pd_valid. "ID_Data_next"should be valid too.
		
		output reg 						ready_read_1,		//to junwei
		output reg 						ready_read_2, 		//to 6
			
		input [COUNTER_WIDTH-1:0]			ram_DOUT1A,		//to from 7
		input [COUNTER_WIDTH-1:0]			ram_DOUT2A,
		
		output reg [COUNTER_WIDTH-1:0]		ram_DIN1A,
		output reg [COUNTER_WIDTH-1:0]		ram_DIN2A,
		
		output reg 						ram_EN1A,
		output reg 						ram_EN2A,
		output reg 						ram_WE1A,
		output reg 						ram_WE2A,
		output reg						ram_REGCE1A,
		output reg						ram_REGCE2A,
		
		output reg [ID_WIDTH-1:0]			ram_ADDR1A,
		output reg [ID_WIDTH-1:0]			ram_ADDR2A
	);
	parameter S0 = 0, S1 = 1, S2 = 2,S3 = 3, S4 = 4, S5 = 5,
					S6 = 6, S7 = 7, S8 = 8, S9 = 9, S10 = 10;
	reg [8:0]								pre_state, next_state;
	reg [TIME_COUNTER_WIDTH - 1 : 0] 		time_counter;
	reg [31:0]                             timePbefor;
	
	wire [LENTH_WIDTH-1:0]					fifo_out_lenth;
	wire [ID_WIDTH-1:0]						fifo_out_id;
	wire 								fifo_empty;
	reg									fifo_rd_en;
	
	reg									ready_write_1;
	reg 									ready_write_2;


	///////////////////////////////////////////////////////////////////////////////////////////////
	always @ (posedge clk) begin
		if(!reset_n) begin
			time_counter	<=	0;
		end else begin
		      if(time_counter == 2*timePbefor)begin
		              time_counter <= 0;
		      end else begin
		              time_counter <= time_counter + 1;
		      end
		end
	end
	///////////////////////////////////////////////////////////////////////////////////////////////
	
	always @(posedge clk) begin
	   if(!reset_n)begin
	       timePbefor <= 500;
	   end else begin
	       if(time_p < 500)begin
	           timePbefor <= 500;
	       end else begin
	           timePbefor <= time_p;
	       end
	   end
	end
	
	///////////////////////////////////////////////////////////////////////////////////////////////
	always @ (posedge clk) begin
		if(!reset_n) begin
			ready_read_1 <= 0;
			ready_read_2 <= 0;
			ready_write_1 <= 0;
			ready_write_2 <= 0;
		end else begin
		if(enable)begin
			if(time_counter >= 10 && time_counter <= (timePbefor - 10)) begin
				ready_read_2 <= 1;
				ready_write_2 <= 0;
				ready_read_1 <= 0;
				ready_write_1 <= 1;	
			end else if(time_counter >= (timePbefor + 10) && time_counter <= 2*timePbefor) begin		
				ready_read_2 <= 0;
				ready_write_2 <= 1;
				ready_read_1 <= 1;
				ready_write_1 <= 0;	
			end else begin
				ready_read_2 <= 0;
				ready_write_2 <= 0;
				ready_read_1 <= 0;
				ready_write_1 <= 0;	
			end
		end	
		end
	end
	
	////////////////////////////////////////////Outputs TO JUNWEI///////////////////////////////////////////////////


	///////////////////////////////////////////////////////////////////////////////////////////////
	
	
	fifo_fall in_fifo
			(// Outputs
			.dout							({fifo_out_lenth, fifo_out_id}),
			.full							(),
			.nearly_full					(),
			.empty						(fifo_empty),
			// Inputs
			.din							({lenth_Data, ID_Data}),
			.wr_en						(valid),
			.rd_en						(fifo_rd_en),
			
			.reset_n						(reset_n),
			.clk							(clk));

	
	
	
//////////////===============================FSM1========================================

	always @ (posedge clk) begin
		if (!reset_n) begin
			pre_state <= S0;
		end else begin
			pre_state <= next_state;
		end
	end

//////////////================================FSM2=======================================

	always @ (*) begin
		case(pre_state)
			S0: begin                   //read one data from BRAM
				if(!fifo_empty && ready_write_1 && enable)
					next_state = S1;
				else if (!fifo_empty && ready_write_2 && enable)
					next_state = S6;
				else
					next_state = S0;
			end
			S1: begin                   //waiting data
				next_state = S2;
			end
			S2: begin                   //waiting data
				next_state = S3;
			end
			S3: begin                   //starting using data from BRAM
				next_state = S4;
			end
			S4: begin
				if(update_c_valid)
					next_state = S5;
				else
					next_state = S4;
			end
			S5: begin
				if(!fifo_empty && ready_write_1)
					next_state = S1;
				else
					next_state = S0;
			end
			S6: begin
				next_state = S7;
			end
			S7: begin
				next_state = S8;
			end
			S8: begin
				next_state = S9;
			end
			S9: begin
				if(update_c_valid)
					next_state = S10;
				else
					next_state = S9;
			end
			S10: begin
				if(!fifo_empty && ready_write_2)
					next_state = S6;
				else
					next_state = S0;
			end
			
		endcase
	end

//////////////=============================FSM3==========================================

	always @(posedge clk) begin
		case(pre_state)
			S0: begin
				if(!fifo_empty && ready_write_1 && enable) begin
					ram_EN1A <= 1;
					ram_REGCE1A <= 1;
					ram_ADDR1A <= fifo_out_id;
				end else if (!fifo_empty && ready_write_2 && enable) begin
					ram_EN2A <= 1;
					ram_REGCE2A <= 1;
					ram_ADDR2A <= fifo_out_id;
				end else begin
					ram_EN1A <= 0;
					ram_EN2A <= 0;
					ram_REGCE1A <= 0;
					ram_REGCE2A <= 0;
					ram_ADDR1A <= 0;
					ram_ADDR2A <= 0;
					
				end
			end
			S1: begin
				//
			end
			S2: begin
				//
				
			end
			S3: begin
				couter_valid <= 1;
				counter_data <= ram_DOUT1A;
				lenth_Data_next <= fifo_out_lenth;
				ID_Data_next <= fifo_out_id;
				fifo_rd_en <= 1;
			end
			S4: begin
				if(update_c_valid)begin
					ram_WE1A <= 1;
					ram_ADDR1A <= update_ID_Data;
					ram_DIN1A <= update_counter_data;
					fifo_rd_en <= 0;
					couter_valid <= 0;
				end	else begin
					fifo_rd_en <= 0;
					couter_valid <= 0;
				end
			end
			S5: begin
				if(!fifo_empty && ready_write_1) begin
					ram_ADDR1A <= fifo_out_id;
					ram_WE1A <= 0;
				end else begin
					ram_WE1A <= 0;
					ram_EN1A <= 0;
				end
			end
			S6: begin
				//	
			end
			S7: begin
				//
			end
			S8: begin
					
				couter_valid <= 1; 		// for calc module
				counter_data <= ram_DOUT2A; 
				lenth_Data_next <= fifo_out_lenth;
				ID_Data_next <= fifo_out_id;
				fifo_rd_en <= 1;	
			end
			S9: begin
				if(update_c_valid)begin
					ram_WE2A <= 1;
					ram_ADDR2A <= update_ID_Data;
					ram_DIN2A <= update_counter_data;
					fifo_rd_en <= 0;
					couter_valid <= 0;
				end	else begin
					fifo_rd_en <= 0;
					couter_valid <= 0;
				end
			end
			S10: begin
				if(!fifo_empty && ready_write_2) begin
					ram_ADDR2A <= fifo_out_id;
					ram_WE2A <= 0;
				end else begin
					ram_WE2A <= 0;
					ram_EN2A <= 0;
				end
			end
			
		endcase
	end
	
endmodule


